#!/usr/bin/env python3
"""
A tool to find and remove duplicate pictures.

Usage:
    duplicate_finder.py add <path> ... [--db=<db_path>] [--parallel=<num_processes>]
    duplicate_finder.py remove <path> ... [--db=<db_path>]
    duplicate_finder.py clear [--db=<db_path>]
    duplicate_finder.py show [--db=<db_path>]
    duplicate_finder.py find [--print] [--match-time] [--trash=<trash_path>] [--db=<db_path>]
    duplicate_finder.py dedup [--confirm] [--match-time] [--trash=<trash_path>]
    duplicate_finder.py -h | --help

Options:
    -h, --help                Show this screen

    --db=<db_path>            The location of the database. (default: ./db)

    --parallel=<num_processes> The number of parallel processes to run to hash the image
                               files (default: 8).

    find:
        --print               Only print duplicate files rather than displaying HTML file
        --match-time          Adds the extra constraint that duplicate images must have the
                              same capture times in order to be considered.
        --trash=<trash_path>  Where files will be put when they are deleted (default: ./Trash)

     dedup:
        --confirm             Confirm you realize this will delete duplicates automatically.
"""


import imagehash
import pymongo
import webbrowser
import os
import shutil
from more_itertools import *
from PIL import Image
from termcolor import colored, cprint
from contextlib import contextmanager
from pymongo import MongoClient
from glob import glob
from multiprocessing import Pool, Value
from functools import partial
from pprint import pprint
from tempfile import TemporaryDirectory
from jinja2 import Template, FileSystemLoader, Environment
from flask import Flask, send_from_directory
from PIL import Image, ExifTags
from subprocess import Popen, PIPE

TRASH = "./Trash/"
DB_PATH = "./db"
NUM_PROCESSES = 8


@contextmanager
def connect_to_db():
    p = Popen(['mongod', '--dbpath', DB_PATH], stdout=PIPE, stderr=PIPE)
    cprint("Started database...", "yellow")
    client = MongoClient()
    db = client.image_database
    images = db.images

    yield images

    client.close()
    cprint("Stopped database...", "yellow")
    p.terminate()


def get_image_files(path):
    def is_image(file_name):
        file_name = file_name.lower()
        return file_name.endswith('.jpg') or  \
            file_name.endswith('.jpeg') or \
            file_name.endswith('.png') or  \
            file_name.endswith('.gif') or  \
            file_name.endswith('.tiff')

    path = os.path.abspath(path)
    for root, dirs, files in os.walk(path):
        for file in files:
            if is_image(file):
                yield os.path.join(root, file)


def hash_file(file, contains_cb, result_cb):
    if contains_cb(file):
        cprint("\tSkipping {}".format(file), "green")
    else:
        try:
            hashes = []
            img = Image.open(file)

            file_size = get_file_size(file)
            image_size = get_image_size(img)
            capture_time = get_capture_time(img)

            # 0 degree hash
            hashes.append(str(imagehash.phash(img)))

            # 90 degree hash
            img = img.rotate(90)
            hashes.append(str(imagehash.phash(img)))

            # 180 degree hash
            img = img.rotate(180)
            hashes.append(str(imagehash.phash(img)))

            # 270 degree hash
            img = img.rotate(270)
            hashes.append(str(imagehash.phash(img)))

            hashes = ''.join(sorted(hashes))
            result_cb(file, hashes, file_size, image_size, capture_time)

            cprint("\tHashed {}".format(file), "blue")
        except OSError:
            cprint("Unable to open {}".format(file), "red")


def hash_files_parallel(files, contains_cb, result_cb):
    with Pool(NUM_PROCESSES) as p:
        func = partial(hash_file,
                       contains_cb=contains_cb,
                       result_cb=result_cb)
        p.map(func, files)


def _add_to_database(file_, hash_, file_size, image_size, capture_time):
    try:
        db.insert_one({"_id": file_,
                       "hash": hash_,
                       "file_size": file_size,
                       "image_size": image_size,
                       "capture_time": capture_time})
    except pymongo.errors.DuplicateKeyError:
        cprint("Duplicate key: {}".format(file), "red")


def _in_database(file):
    return db.count({"_id": file}) > 0


def add(paths, db):
    for path in paths:
        cprint("Hashing {}".format(path), "blue")
        files = get_image_files(path)

        hash_files_parallel(files, _in_database, _add_to_database)

        cprint("...done", "blue")


def remove(paths, db):
    for path in paths:
        files = get_image_files(path)

        # TODO: Can I do a bulk delete?
        for file in files:
            db.delete_one({'_id': file})


def remove_image(file, db):
    db.delete_one({'_id': file})


def clear(db):
    db.drop()


def show(db):
    total = db.count()
    pprint(list(db.find()))
    print("Total: {}".format(total))


def same_time(dup):
    items = dup['items']
    if "Time unknown" in items:
        # Since we can't know for sure, better safe than sorry
        return True

    if len(set([i['capture_time'] for i in items])) > 1:
        return False

    return True


def find(db, print_, match_time):
    dups = db.aggregate([
        {"$group":
            {
                "_id": "$hash",
                "total": {"$sum": 1},
                "items":
                    {
                        "$push":
                            {
                                "file_name": "$_id",
                                "file_size": "$file_size",
                                "image_size": "$image_size",
                                "capture_time": "$capture_time"
                            }
                }
            }
         },
        {"$match":
            {
                "total": {"$gt": 1}
            }
         }])

    dups = list(dups)

    if match_time:
        dups = [d for d in dups if same_time(d)]

    if print_:
        pprint(dups)
        print("Number of duplicates: {}".format(len(dups)))
    else:
        display_duplicates(dups, partial(remove_image, db=db))


def dedup(db, match_time):
    dups = db.aggregate([
        {"$group":
            {
                "_id": "$hash",
                "total": {"$sum": 1},
                "items":
                    {
                        "$push":
                            {
                                "file_name": "$_id",
                                "file_size": "$file_size",
                                "image_size": "$image_size",
                                "capture_time": "$capture_time"
                            }
                }
            }
         },
        {"$match":
            {
                "total": {"$gt": 1}
            }
         }])

    dups = list(dups)

    if match_time:
        dups = [d for d in dups if same_time(d)]

    retrn_dups = []
    cb = partial(remove_image, db=db)
    for dup in dups:
        retrn_dups += [do_delete_picture(x['file_name'], cb)
                       for x in dup['items'][1:]]

    print("deleted {}/{} files".format(retrn_dups.count("True"),
                                       len(retrn_dups)))


def do_delete_picture(file_name, delete_cb):
    print("Moving file")
    file_name = "/" + file_name
    if not os.path.exists(TRASH):
        raise Exception("path to trash missing: {}".format(TRASH))
    try:
        print(file_name)
        print(TRASH + os.path.basename(file_name))
        shutil.move(file_name, TRASH + os.path.basename(file_name))
        delete_cb(file_name)
    except FileNotFoundError:
        print("file not found {}".format(file_name))
        return "False"
    except Exception as e:
        print("error {}".format(str(e)))
        return "False"

    return "True"


def display_duplicates(duplicates, delete_cb):
    with TemporaryDirectory() as folder:
        # Generate all of the HTML files
        chunk_size = 25
        for i, dups in enumerate(chunked(duplicates, chunk_size)):
            with open('{}/{}.html'.format(folder, i), 'w') as f:
                f.write(render(dups, current=i, total=int(
                    len(duplicates) / chunk_size)))

        webbrowser.open("file://{}/{}".format(folder, '0.html'))

        app = Flask(__name__)
        @app.route('/picture/<path:file_name>', methods=['DELETE'])
        def delete_picture(file_name):
            return do_delete_picture(file_name)

        app.run()


def get_file_size(file_name):
    try:
        return os.path.getsize(file_name)
    except FileNotFoundError:
        return 0


def get_image_size(img):
    return "{} x {}".format(*img.size)


def get_capture_time(img):
    try:
        exif = {
            ExifTags.TAGS[k]: v
            for k, v in img._getexif().items()
            if k in ExifTags.TAGS
        }
        return exif["DateTimeOriginal"]
    except:
        return "Time unknown"


def render(duplicates, current, total):

    env = Environment(loader=FileSystemLoader('template'))
    template = env.get_template('index.html')

    return template.render(duplicates=duplicates, current=current, total=total)

if __name__ == '__main__':
    from docopt import docopt
    args = docopt(__doc__)

    if args['--trash']:
        TRASH = args['--trash']

    if args['--db']:
        DB_PATH = args['--db']

    if args['--parallel']:
        NUM_PROCESSES = args['--parallel']

    with connect_to_db() as db:
        if args['add']:
            add(args['<path>'], db)
        elif args['remove']:
            remove(args['<path>'], db)
        elif args['clear']:
            clear(db)
        elif args['show']:
            show(db)
        elif args['find']:
            find(db, args['--print'], args['--match-time'])
        elif args['dedup']:
            if not args['--confirm']:
                print("must --confirm you will dedup files")
            else:
                dedup(db, args['--match-time'])
