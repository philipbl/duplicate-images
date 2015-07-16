#!/usr/bin/env python3
"""
Uses phash to find duplicate pictures.

Usage:
    duplicate_finder.py add <path> [--ignore | --error] [--database=<db_file>]
    duplicate_finder.py remove <path> [--database=<db_file>]
    duplicate_finder.py clear [--database=<db_file>]
    duplicate_finder.py show [--database=<db_file>]
    duplicate_finder.py find [--print] [--database=<db_file>]
    duplicate_finder.py -h | –-help

Options:
    -h, -–help      Show this screen
    --ignore        Ignore an image file if it has already been hashed (default)
    --errors        Display an error if an image file has already been hashed,
                    but continuing calculating hashes for other images
    --print         Only print duplicate files
    -–database=<db> Set database file [default: ./dups.db]
"""


import imagehash
import pymongo
from PIL import Image
from termcolor import colored, cprint
from contextlib import contextmanager
from pymongo import MongoClient
from glob import glob
from enum import Enum
from multiprocessing import Pool, Value
from functools import partial
from pprint import pprint


class DuplicateType(Enum):
    ignore = 1
    error = 2

DEFAULT_DATABASE = "hashes.db"
DUPLICATE_TYPE = DuplicateType.ignore

@contextmanager
def connect_to_db():
    # Start database
    # mongod --config /usr/local/etc/mongod.conf

    client = MongoClient()
    db = client.image_database
    images = db.images

    yield images

    client.close()
    # Stop database

def get_image_files(path):
    # TODO: Add more file types
    files = glob(path + '/*.jpg') + \
            glob(path + '/*.JPG') + \
            glob(path + '/*.png') + \
            glob(path + '/*.PNG')
    return files

def hash_file(file, cb):
    cb(file, str(imagehash.phash(Image.open(file))))

def hash_files_single(files, cb):
    for file in files:
        hash_file(file, cb)

def hash_files_parallel(files, cb):
    with Pool(8) as p:
        func = partial(hash_file, cb=cb)
        p.map(func, files)

def _add_to_database(file, hash):
    try:
        db.insert_one({"_id": file, "hash": hash})
    except pymongo.errors.DuplicateKeyError:
        if DUPLICATE_TYPE == DuplicateType.ignore:
            pass
        elif DUPLICATE_TYPE == DuplicateType.error:
            cprint("Duplicate key: {}".format(file), "red")

def add(path, db):
    cprint("Hashing {}".format(path), "blue")
    files = get_image_files(path)

    # hash_files_single(files, _add_to_database)
    hash_files_parallel(files, _add_to_database)

    cprint("...done", "blue")


def remove(path, db):
    files = get_image_files(path)

    # TODO: Can I do a bulk delete?
    for file in files:
        db.delete_one({'_id': file})

def clear(db):
    db.remove({})

def show(db):
    pprint(list(db.find()))

def find(db, print_):
    result = db.aggregate([
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
        pprint(list(result))
    else:
        pass

if __name__ == '__main__':
    from docopt import docopt
    args = docopt(__doc__)
    database = args['--database']

    if database is None:
        database = DEFAULT_DATABASE

    if args['--ignore']:
        DUPLICATE_TYPE = DuplicateType.ignore
    elif args['--error']:
        DUPLICATE_TYPE = DuplicateType.error

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



