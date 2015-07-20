#!/usr/bin/env python3
"""
A tool to find and remove duplicate pictures.

Usage:
    duplicate_finder.py add <path> ...
    duplicate_finder.py remove <path> ...
    duplicate_finder.py clear
    duplicate_finder.py show
    duplicate_finder.py find [--print] [--trash=<trash_path>]
    duplicate_finder.py -h | –-help

Options:
    -h, -–help            Show this screen

    find:
        --print               Only print duplicate files rather than displaying HTML file
        --trash=<trash_path>  Where files will be put when they are deleted (default: ./Trash)
"""


import imagehash
import pymongo
import webbrowser
import os
import shutil
from PIL import Image
from termcolor import colored, cprint
from contextlib import contextmanager
from pymongo import MongoClient
from glob import glob
from multiprocessing import Pool, Value
from functools import partial
from pprint import pprint
from tempfile import NamedTemporaryFile
from jinja2 import Template, FileSystemLoader, Environment
from flask import Flask, send_from_directory
from PIL import Image, ExifTags
from subprocess import Popen

TRASH = "./Trash/"


@contextmanager
def connect_to_db():
    p = Popen(['mongod', '--config', 'mongod.conf'])
    cprint("Started database...", "yellow")
    client = MongoClient()
    db = client.image_database
    images = db.images

    yield images

    client.close()
    cprint("Stopped database...", "yellow")
    p.kill()


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

            # 0 degree hash
            img = Image.open(file)
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
            result_cb(file, hashes)

            cprint("\tHashed {}".format(file), "blue")
        except OSError:
            cprint("Unable to open {}".format(file), "red")


def hash_files_parallel(files, contains_cb, result_cb):
    with Pool(8) as p:
        func = partial(hash_file,
                       contains_cb=contains_cb,
                       result_cb=result_cb)
        p.map(func, files)


def _add_to_database(file, hash):
    try:
        db.insert_one({"_id": file, "hash": hash})
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
    db.remove({})


def show(db):
    total = db.count()
    pprint(list(db.find()))
    print("Total: {}".format(total))


def find(db, print_):
    dups = db.aggregate([
        {"$group":
            {
                "_id": "$hash",
                "total": {"$sum": 1},
                "file_names": {"$push": "$_id"}
            }
        },
        {"$match":
            {
                "total" : {"$gt": 1}
            }
        }])

    if print_:
        pprint(list(dups))
    else:
        display_duplicates(list(dups), partial(remove_image, db=db))

def display_duplicates(duplicates, delete_cb):
    with NamedTemporaryFile(mode='w', suffix='.html') as f:
        f.write(render(duplicates))
        webbrowser.open("file://{}".format(f.name))

        app = Flask(__name__)
        @app.route('/picture/<path:file_name>', methods=['DELETE'])
        def delete_picture(file_name):
            print("Moving file")
            file_name = "/" + file_name

            try:
                print(file_name)
                print(TRASH + os.path.basename(file_name))
                shutil.move(file_name, TRASH + os.path.basename(file_name))
                delete_cb(file_name)
            except FileNotFoundError:
                return "False"

            return "True"

        app.run()


def render(duplicates):
    def get_file_size(file_name):
        try:
            return os.path.getsize(file_name)
        except FileNotFoundError:
            return 0

    def get_image_size(file_name):
        try:
            im = Image.open(file_name)
            return "{} x {}".format(*im.size)
        except FileNotFoundError:
            return "Size unknown"

    def get_capture_time(file_name):
        try:
            img = Image.open(file_name)
            exif = {
                ExifTags.TAGS[k]: v
                for k, v in img._getexif().items()
                if k in ExifTags.TAGS
            }
            return exif["DateTimeOriginal"]
        except:
            return "Time unknown"

    env = Environment(loader=FileSystemLoader('template'))

    # Add my own filters
    env.filters['file_size'] = get_file_size
    env.filters['image_size'] = get_image_size
    env.filters['capture_time'] = get_capture_time

    template = env.get_template('index.html')

    return template.render(duplicates=duplicates)

if __name__ == '__main__':
    from docopt import docopt
    args = docopt(__doc__)

    if args['--trash']:
        TRASH = args['--trash']

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
            find(db, args['--print'])



