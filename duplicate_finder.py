#!/usr/bin/env python3
"""
A tool to find and remove duplicate pictures.

Usage:
    duplicate_finder.py add <path> ... [--db=<db_path>] [--parallel=<num_processes>]
    duplicate_finder.py remove <path> ... [--db=<db_path>]
    duplicate_finder.py clear [--db=<db_path>]
    duplicate_finder.py show [--db=<db_path>]
    duplicate_finder.py cleanup [--db=<db_path>]
    duplicate_finder.py find [--print] [--delete] [--match-time] [--trash=<trash_path>] \
[--db=<db_path>] [--threshold=<num>]
    duplicate_finder.py -h | --help

Options:
    -h, --help                Show this screen

    --db=<db_path>            The location of the database or a MongoDB URI. (default: ./db)

    --parallel=<num_processes> The number of parallel processes to run to hash the image
                               files (default: number of CPUs).

    find:
        --threshold=<num>     Image matching threshold. Number of different bits in Hamming \
distance. False positives are possible.
        --print               Only print duplicate files rather than displaying HTML file
        --delete              Move all found duplicate pictures to the trash. This option \
takes priority over --print.
        --match-time          Adds the extra constraint that duplicate images must have the
                              same capture times in order to be considered.
        --trash=<trash_path>  Where files will be put when they are deleted (default: ./Trash)
"""

import concurrent.futures
from contextlib import contextmanager
import os
import math
from pprint import pprint
import shutil
from subprocess import Popen, PIPE, TimeoutExpired
import sys
from tempfile import TemporaryDirectory

import webbrowser
import binascii
import io
from jinja2 import FileSystemLoader, Environment
from flask import Flask, Response
from flask_cors import CORS


from more_itertools import chunked
import pymongo
from PIL import Image
import pybktree
from termcolor import cprint

from hashers import BinaryHasher, ImageHasher


def get_hashers() -> list:
    """Return array of active hashers"""
    return [
        BinaryHasher(),
        ImageHasher(),
    ]


@contextmanager
def connect_to_db(db_conn_string='./db'):
    """Connect to mongo"""
    p = None

    # Determine db_conn_string is a mongo URI or a path
    # If this is a URI
    if 'mongodb://' == db_conn_string[:10] or 'mongodb+srv://' == db_conn_string[:14]:
        client = pymongo.MongoClient(db_conn_string)
        cprint("Connected server...", "yellow")
        db = client.image_database
        images = db.images

    # If this is not a URI
    else:
        if not os.path.isdir(db_conn_string):
            os.makedirs(db_conn_string)

        p = Popen(['mongod', '--dbpath', db_conn_string],
                  stdout=PIPE, stderr=PIPE)

        try:
            p.wait(timeout=2)
            stdout, _ = p.communicate()
            cprint("Error starting mongod", "red")
            cprint(stdout.decode(), "red")
            sys.exit()
        except TimeoutExpired:
            pass

        cprint("Started database...", "yellow")
        client = pymongo.MongoClient()
        db = client.image_database
        images = db.images

    yield images

    client.close()

    if p is not None:
        cprint("Stopped database...", "yellow")
        p.terminate()


def get_files(path: str):
    """
    Check path recursively for files and yield full path.

    :param path:
    :return: yield absolute path
    """
    path = os.path.abspath(path)
    for root, _, files in os.walk(path):
        for file in files:
            file = os.path.join(root, file)
            yield file


def hash_file(file_path: str):
    """Hash file with all hashers"""
    hashes = []
    meta = {}
    hashers = get_hashers()

    try:
        for hasher in hashers:
            if hasher.is_applicable(file_path):
                with open(file_path, 'rb') as file_object:
                    (new_hashes, new_meta) = hasher.hash(file_object)
                    hashes = hashes + new_hashes
                    meta = meta | new_meta

        cprint(f'\tHashed {file_path}', "blue")
    except OSError:
        cprint(f'\tUnable to open {file_path}', "red")
        return None

    return file_path, (
        hashes,
        meta
    )


def hash_files_parallel(files, num_processes=None):
    """Hash files in parallel in subprocesses"""
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
        for result in executor.map(hash_file, files):
            if result is not None:
                yield result


def _add_to_database(file_path: str, hashes_meta: tuple, db):
    """Add hashes and meta information of a file to database"""
    (hashes, meta) = hashes_meta
    try:
        db.insert_one({"_id": file_path,
                       "hashes": hashes,
                       "meta": meta,
                       })
    except pymongo.errors.DuplicateKeyError:
        cprint(f'Duplicate key: {file_path}', "red")


def _in_database(file, db):
    """Return if file exists in database"""
    return db.count_documents({"_id": file}) > 0


def new_files(files, db):
    """yield only new files, already hashed files are skipped"""
    for file_path in files:
        if _in_database(file_path, db):
            cprint(f'\tAlready hashed {file_path}', "green")
        else:
            yield file_path


def add(paths, db, num_processes=None):
    """Lopp through files and add hash them"""
    for path in paths:
        cprint(f'Hashing {path}', "blue")
        files = get_files(path)
        files = new_files(files, db)

        for result in hash_files_parallel(files, num_processes):
            _add_to_database(*result, db=db)

        cprint("...done", "blue")


def remove(paths, db):
    """Remove file from database"""
    for path in paths:
        files = get_files(path)
        for file in files:
            remove_file(file, db)


def remove_file(file, db):
    """Remove file from database"""
    db.delete_one({'_id': file})


def remove_image(file, db):
    """Remove file from database"""
    db.delete_one({'_id': file})


def clear(db):
    """Clear database"""
    db.drop()


def show(db):
    """Show all files from the databse"""
    total = db.count_documents({})
    pprint(list(db.find()))
    print(f'Total: {total}')


def cleanup(db):
    """Clean disappeared files from the database"""
    count = 0
    files = db.find()
    for _id in files:
        file_name = _id['_id']
        if not os.path.exists(file_name):
            remove_image(file_name, db)
            count += 1
    cprint(f'Cleanup removed {count} files', 'yellow')


def same_time(dup):
    """Check if capture_time meta attribute is the same"""
    items = dup['items']

    if len({(i['meta']['capture_time'] if 'capture_time' in i['meta'] else '') for i in items})>1:
        return False

    return True


def find(db, match_time=False):
    """Find duplictes by equal hashes"""
    dups = db.aggregate([
        {"$unwind": "$hashes"},
        {
            "$group": {
                "_id": "$hashes",
                "total": {"$sum": 1},
                "file_size": {"$max": "$meta.file_size"},
                "items": {
                    "$push": {
                        "file_name": "$_id",
                        "meta": "$meta",
                    }
                }
            }
        },
        {
            "$match": {
                "total": {"$gt": 1}
            }
        },
        {"$sort": {"file_size": -1}}
    ])

    if match_time:
        dups = (d for d in dups if same_time(d))

    return list(dups)


def find_threshold(db, threshold=1):
    """Find duplicates by number of bits of Humming distance"""
    dups = []
    # Build a tree
    tree = pybktree.BKTree(pybktree.hamming_distance)

    cprint('Finding fuzzy duplicates, it might take a while...')
    cnt = 0
    for document in db.find():
        for doc_hash in document['hashes']:
            int_hash = int.from_bytes(doc_hash, "big")
            tree.add(int_hash)
        cnt = cnt + 1

    deduplicated = set()

    scanned = 0
    for document in db.find():
        cprint(f'\r{(scanned * 100 / (cnt - 1))}%', end='')
        scanned = scanned + 1
        max_size = document['meta']['file_size']
        for doc_hash in document['hashes']:
            if doc_hash in deduplicated:
                continue
            deduplicated.add(doc_hash)
            int_hash = int.from_bytes(doc_hash, "big")

            similar = tree.find(int_hash, threshold)
            if len(similar) > 1:
                similar = list(set(similar))

                similars = []
                for (distance, item_hash) in similar:
                    if distance > 0:
                        deduplicated.add(item_hash)

                    for item in db.find({'hashes': binascii.unhexlify(hex(item_hash)[2:])}):
                        item['file_name'] = item['_id']
                        similars.append(item)
                        max_size = max_size if item['meta']['file_size'] <= max_size \
                            else item['meta']['file_size']
                if len(similars) > 0:
                    dups.append(
                        {
                            '_id': doc_hash,
                            'total': len(similars),
                            'items': similars,
                            'file_size': max_size
                        }
                    )

    return dups


def delete_duplicates(duplicates, db):
    """Delete duplicates except the first one"""
    results = [delete_picture(x['file_name'], db)
               for dup in duplicates for x in dup['items'][1:]]
    cprint(f'Deleted {results.count(True)}/{len(results)} files', 'yellow')


def delete_picture(file_name, db, trash="./Trash/"):
    """Delete picture file and from the database"""
    cprint(f'Moving {file_name} to {trash}', 'yellow')
    if not os.path.exists(trash):
        os.makedirs(trash)
    try:
        shutil.move(file_name, trash + os.path.basename(file_name))
        remove_image(file_name, db)
    except FileNotFoundError:
        cprint(f'File not found {file_name}', 'red')
        return False
    except Exception as e:
        cprint(f'Error: {str(e)}', 'red')
        return False

    return True


def transpose_duplicagtes(duplicates):
    """Transpose duplictes to render in columns"""
    for group in duplicates:
        items_clount = len(group['items'])
        row = {
            'id': [''] * items_clount,
            'file_name': [''] * items_clount,
        }
        index = 0
        for image in group['items']:
            row['id'][index] = image['file_name']
            row['file_name'][index] = image['file_name']
            for key, value in image['meta'].items():
                if key not in row:
                    row[key] = [''] * items_clount
                row[key][index] = value
            index += 1
        group['items'] = row

    return duplicates


def display_duplicates(duplicates, db, trash="./Trash/"):
    """Displays duplicates in browser"""
    duplicates = transpose_duplicagtes(duplicates)
    app = Flask(__name__)
    CORS(app)

    def render(duplicates, current, total):
        env = Environment(loader=FileSystemLoader('template'))
        template = env.get_template('index.html')
        return template.render(duplicates=duplicates,
                               current=current,
                               total=total)

    with TemporaryDirectory() as folder:
        # Generate all of the HTML files
        chunk_size = 25
        for i, dups_page in enumerate(chunked(duplicates, chunk_size)):
            with open(f'{folder}/{i}.html', 'w', encoding="utf-8") as f:
                f.write(render(dups_page,
                               current=i,
                               total=math.ceil(len(duplicates) / chunk_size)))

        webbrowser.open(f'file://{folder}/0.html')

        @app.route('/picture/<path:file_name>', methods=['DELETE'])
        def delete_picture_(file_name, trash=trash):
            return str(delete_picture('/' + file_name, db, trash))

        @app.route('/heic-transform/<path:file_name>', methods=['GET'])
        def transcode_heic_(file_name):
            heif_image = Image.open('/' + file_name)
            encoded = io.BytesIO()
            heif_image.save(encoded, format='JPEG')
            return Response(encoded.getvalue(), mimetype='image/jpeg')

        app.run()


if __name__ == '__main__':
    from docopt import docopt
    args = docopt(__doc__)

    if args['--trash']:
        TRASH = args['--trash']
    else:
        TRASH = "./Trash/"

    if args['--db']:
        DB_PATH = args['--db']
    else:
        DB_PATH = "./db"

    if args['--parallel']:
        NUM_PROCESSES = int(args['--parallel'])
    else:
        NUM_PROCESSES = None

    with connect_to_db(db_conn_string=DB_PATH) as main_db:
        if args['add']:
            add(args['<path>'], main_db, NUM_PROCESSES)
        elif args['remove']:
            remove(args['<path>'], main_db)
        elif args['clear']:
            clear(main_db)
        elif args['cleanup']:
            cleanup(main_db)
        elif args['show']:
            show(main_db)
        elif args['find']:
            if args['--threshold'] is not None:
                main_dups = find_threshold(main_db, int(args['--threshold']))
            else:
                main_dups = find(main_db, args['--match-time'])

            if args['--delete']:
                delete_duplicates(main_dups, main_db)
            elif args['--print']:
                pprint(main_dups)
                print(f'Number of duplicates: {len(main_dups)}')
            else:
                display_duplicates(main_dups, db=main_db)
