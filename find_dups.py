#!/usr/bin/env python3

from glob import iglob, glob
from pprint import pprint
from PIL import Image
import imagehash as ihash
import pickle
import os.path
from multiprocessing import Pool

def create_hash(index_and_file_name):
    index, file_name = index_and_file_name
    image = Image.open(file_name)
    hash_ = str(ihash.phash(image))
    print(index)

    return (file_name, hash_)

def hash_directory(dir_):
    files = glob(dir_ + '/*.jpg') + glob(dir_ + '/*.JPG') + glob(dir_ + '/*.png') + glob(dir_ + '/*.PNG')

    with Pool(8) as p:
        hashes = p.map(create_hash, enumerate(files))

    return dict(hashes)


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

####### SAVE HASHES
# ios_hashes = hash_directory('/Volumes/Pictures/Original/iOS Pictures')
# with open('ios_pictures.pickle', 'wb') as f:
#     pickle.dump(ios_hashes, f)

# print("Done hashing iOS pictures\n")

# bridget_hashes = hash_directory('/Volumes/Pictures/Original/bridgets-iphone-backup-pictures')
# with open('bridget_pictures.pickle', 'wb') as f:
#     pickle.dump(bridget_hashes, f)

# print("Done hashing Bridget's iOS  pictures")


####### LOAD HASHES
def load_hash(name):
    with open(name, 'rb') as f:
        return pickle.load(f)

ios_hashes = load_hash('ios_pictures.pickle')
bridget_hashes = load_hash('bridget_pictures.pickle')

dups = find_dups(ios_hashes)
pprint(len(dups))
pprint(sum([len(x) for x in dups]))

dups = find_dups(bridget_hashes)
pprint(len(dups))
pprint(sum([len(x) for x in dups]))

dups = find_dups(ios_hashes, bridget_hashes)
pprint(len(dups))
pprint(sum([len(x) for x in dups]))
pprint(dups)

# for hash_, img_list in hashes.items():
#     if len(img_list) > 1:
#         print(" ".join(img_list))
