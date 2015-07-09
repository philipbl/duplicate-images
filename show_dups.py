#!/usr/bin/env python3

import pickle
from jinja2 import Template, FileSystemLoader, Environment
from flask import Flask

app = Flask(__name__)

def load_hash(name):
    with open(name, 'rb') as f:
        return pickle.load(f)

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

@app.route('/')
def show_dups():
    ios_hashes = load_hash('ios_pictures.pickle')
    bridget_hashes = load_hash('bridget_pictures.pickle')
    dups = find_dups(ios_hashes, bridget_hashes)

    dups = dups[:1]

    env = Environment(loader=FileSystemLoader('template'))
    template = env.get_template('index.html')

    return template.render(duplicates=dups)

@app.route('/picture/<path:file_name>', methods=['DELETE'])
def delete_picture(file_name):
    file_name = "/" + file_name
    print(file_name)
    return "True"

if __name__ == '__main__':
    app.run(debug=True)
