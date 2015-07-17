#!/usr/bin/env python3

import pickle
import os
import shutil
import webbrowser
from jinja2 import Template, FileSystemLoader, Environment
from flask import Flask, send_from_directory
from PIL import Image, ExifTags
from tempfile import NamedTemporaryFile
import webbrowser

TRASH = "./Trash/"

app = Flask(__name__)

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

    def run():

        # with open('index.html', 'w') as f:
        with NamedTemporaryFile(mode='w', suffix='.html') as f:
            f.write(self.render())
            webbrowser.open("file://{}".format(f.name))

        # self.app.run(debug=True)
