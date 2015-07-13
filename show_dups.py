#!/usr/bin/env python3

import pickle
import os
import shutil
import webbrowser
from jinja2 import Template, FileSystemLoader, Environment
from flask import Flask, send_from_directory
from PIL import Image, ExifTags

TRASH = "./Trash/"

app = Flask(__name__)

def load_hash(name):
    with open(name, 'rb') as f:
        return pickle.load(f)

ios_hashes = load_hash('ios_pictures.pickle')
bridget_hashes = load_hash('bridget_pictures.pickle')

def find_dups(*datas):
    hashes = {}
    for data in datas:
        for image_name, hash_ in data.items():
            hashes[hash_] = hashes.get(hash_, []) + [image_name]

        duplicates = []
        for hash_, image_names in hashes.items():
            if len(image_names) > 1:
                duplicates.append(image_names)

    return duplicates

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
        return "0 x 0"

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
        return "Time Unknown"

def render():
    dups = find_dups(ios_hashes, bridget_hashes)

    env = Environment(loader=FileSystemLoader('template'))

    # Add my own filters
    env.filters['file_size'] = get_file_size
    env.filters['image_size'] = get_image_size
    env.filters['capture_time'] = get_capture_time

    template = env.get_template('index.html')

    return template.render(duplicates=dups)

@app.route('/picture/<path:file_name>', methods=['DELETE'])
def delete_picture(file_name):
    print("Moving file")
    file_name = "/" + file_name

    try:
        print(file_name)
        print(TRASH + os.path.basename(file_name))
        shutil.move(file_name, TRASH + os.path.basename(file_name))
    except FileNotFoundError:
        return "False"

    return "True"

if __name__ == '__main__':
    with open('index.html', 'w') as f:
        f.write(render())

    webbrowser.open('index.html')
    app.run(debug=True)
