#!/usr/bin/env python3

from glob import iglob, glob
from pprint import pprint
from PIL import Image
import imagehash as ihash
import pickle
import os.path

def hash_directory(dir_, cache):

    if os.path.isfile(cache):
        with open(cache, 'rb') as f:
            hashes = pickle.load(f)
    else:
        hashes = {}

    try:
        files = glob(dir_ + '/*.jpg') + glob(dir_ + '/*.JPG') + glob(dir_ + '/*.png') + glob(dir_ + '/*.PNG')
        total_files = len(files)

        for i, file_name in enumerate(files):
            if file_name in hashes:
                continue

            image = Image.open(file_name)
            hash_ = str(ihash.phash(image))
            hashes[file_name] = hash_

            print("{}/{}".format(i, total_files))

    except KeyboardInterrupt:
        pass
    finally:
        print("Saving...")
        with open(cache, 'wb') as f:
            pickle.dump(hashes, f)

    return hashes


def find_dups(data):
    hashes = {}
    for image_name, hash_ in data.items():
        hashes[hash_] = hashes.get(hash_, []) + [image_name]

    duplicates = []
    for hash_, image_names in hashes.items():
        if len(image_names) > 1:
            duplicates.append(image_names)

    return duplicates


ios_hashes = hash_directory('/Volumes/Pictures/Original/iOS Pictures', 'ios_pictures.pickle')
bridget_hashes = hash_directory('/Volumes/Pictures/Original/bridgets-iphone-backup-pictures', 'bridget_pictures.pickle')
# dups = find_dups(ios_hashes)

# pprint(dups)


# for hash_, img_list in hashes.items():
#     if len(img_list) > 1:
#         print(" ".join(img_list))
