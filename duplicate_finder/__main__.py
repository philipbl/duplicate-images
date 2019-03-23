import functools
import json
import os
from pprint import pprint
import shutil
import sys

import click
import psutil
from termcolor import cprint

from database.mongodb import MongoDB
from database.sqlite import SQLite
from database.tinydb import TinyDB
import display
import images


DBs = {'mongodb': MongoDB,
       'sqlite': SQLite,
       'tinydb': TinyDB}

DB_LOCATIONS = {'mongodb': 'mongodb://localhost:27017',
                'sqlite': './db.sqlite',
                'tinydb': './db.json'}

def print_info(str):
    cprint(str, "blue", file=sys.stderr)

def print_warning(str):
    cprint(str, "yellow", file=sys.stderr)

def print_error(str):
    cprint(str, "red", file=sys.stderr)



@click.group()
@click.version_option(version='1.0')
@click.option('--db', type=click.Choice(sorted(DBs.keys())),
              default='tinydb', show_default=True)
@click.option('--db-location',
              help='The location of the database. This will change depending on the '
                   'database used. [defaults {}]'.format(
                        ', '.join(["{}: {}".format(name, loc)
                                   for name, loc in sorted(DB_LOCATIONS.items())])))
@click.pass_context
def cli(ctx, db, db_location):
    ctx.obj = DBs[db](DB_LOCATIONS[db])


@cli.command(short_help="Processes all images in given path(s), adding them to the database.")
@click.argument('paths', nargs=-1, type=click.Path(exists=True))
@click.option('--parallel', default=psutil.cpu_count(), show_default=True)
@click.pass_obj
def add_paths(db, paths, parallel):
    def new_image_files(files):
        for file in files:
            if db.contains(file):
                print_info("\tAlready hashed {}".format(file))
            else:
                yield file

    for path in paths:
        print_info("Hashing {}".format(path))

        files = images.get_image_files(path)
        files = new_image_files(files)

        for file, result in images.hash_files(files, parallel):
            if result is None:
                print_error("\tUnable to open {}".format(file))
                continue

            print_info("\tHashed {}".format(file))
            db.insert(result)

        print_info("...done")


@cli.command(short_help="Removes all images information in the given path(s) from database.")
@click.argument('paths', nargs=-1, type=click.Path(exists=True))
@click.pass_obj
def remove_paths(db, paths):
    total = 0

    for path in paths:
        print_info("Removing image files in database from {}".format(path))
        files = images.get_image_files(path)

        for file in files:
            print_info("\tRemoving {}".format(file))
            db.remove(file)
            total += 1
        print_info("...done")

    print_info("Images removed in database: {}".format(total))


@cli.command(short_help="Clears database.")
@click.confirmation_option(prompt="Are you sure you want to clear the database?")
@click.pass_obj
def clear_db(db):
    db.clear()
    print_info("Database was cleared")


@cli.command(short_help="Prints out all image information stored in database.")
@click.pass_obj
def show_db(db):
    pprint(db.all())
    print_info("Total: {}".format(db.count()))


@cli.command(name='display',
             short_help='Display images in webpage.')
@click.option('--trash', type=click.Path(),
              default='./Trash', show_default=True,
              help='Path to where files will be put when they are deleted.')
@click.option('--match-time', is_flag=True,
              help='Adds the extra constraint that duplicate images must have '
                   'the same capture times in order to be considered.')
@click.pass_obj
def display_(db, trash, match_time):
    print_info("Finding duplicates...")
    duplicates = db.find_duplicates(match_time)
    print_info("...done")

    # If no options were set, display duplicates
    delete_cb = functools.partial(delete_image, db=db, trash=trash)
    display.display_duplicates(duplicates, delete_cb)


@cli.command(short_help='Automatically delete duplicate images.')
@click.option('--trash', type=click.Path(),
              default='./Trash', show_default=True,
              help='Path to where files will be put when they are deleted.')
@click.option('--match-time', is_flag=True,
              help='Adds the extra constraint that duplicate images must have '
                   'the same capture times in order to be considered.')
@click.pass_obj
def delete(db, trash, match_time):
    if not click.confirm('Are you sure you want to delete all duplicate images?'):
        click.echo("Aborted!")
        return

    print_info("Finding duplicates...")
    duplicates = db.find_duplicates(match_time)
    print_info("...done")

    trash = os.path.normpath(trash)
    os.makedirs(trash, exist_ok=True)

    print_info("Deleting duplicates...")
    results = []
    for dup in duplicates:
        for file_info in dup['items'][1:]:
            results.append(delete_image(file_info['file_name'], db, trash))

    print_info("\tDeleted {}/{} files".format(results.count(True),
                                              len(results)))
    print_info("...done")


@cli.command(name='print',
             short_help='Prints out all duplicate images found.')
@click.option('--match-time', is_flag=True,
              help='Adds the extra constraint that duplicate images must have '
                   'the same capture times in order to be considered.')
@click.pass_obj
def print_(db, match_time):
    print_info("Finding duplicates...")
    duplicates = db.find_duplicates(match_time)
    print_info("...done")

    print(json.dumps(duplicates, indent=2))
    print_info("Number of duplicates: {}".format(len(duplicates)))


def delete_image(file_name, db, trash):
    print_warning("\tMoving {} to {}".format(file_name, trash))

    os.makedirs(trash, exist_ok=True)

    try:
        print(os.path.join(trash, os.path.basename(file_name)))
        shutil.move(file_name, os.path.join(trash, os.path.basename(file_name)))
        db.remove(file_name)
    except FileNotFoundError as e:
        print_error(f"\t{e}")
        return False
    except Exception as e:
        print_error("\tError: {}".format(str(e)))
        return False

    return True


if __name__ == '__main__':
    cli()
