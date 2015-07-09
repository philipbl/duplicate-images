#!/usr/bin/env python3

import pickle
from jinja2 import Template, FileSystemLoader, Environment

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

ios_hashes = load_hash('ios_pictures.pickle')
bridget_hashes = load_hash('bridget_pictures.pickle')
dups = find_dups(ios_hashes, bridget_hashes)

env = Environment(loader=FileSystemLoader('template'))
template = env.get_template('index.html')

with open('output/index.html', 'w') as f:
    f.write(template.render(duplicates=dups))
