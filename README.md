# Duplicate Image Finder

![](https://api.travis-ci.org/philipbl/duplicate-images.svg)

This Python script finds duplicate images using a [perspective hash (pHash)](http://www.phash.org) to compare images. pHash ignores the image size and file size and instead creates a hash based on the pixels of the image. This allows you to find duplicate pictures that have been rotated, have changed metadata, and slightly edited.

This script hashes images added to it, storing the hash into a database (MongoDB). To find duplicate images, hashes are compared. If the hash is the same between two images, then they are marked as duplicates. A web interface is provided to delete duplicate images easily. If you are feeling lucky, there is an option to automatically delete duplicate files.

As a word of caution, pHash is not perfect. I have found that duplicate pictures sometimes have different hashes and similar (but not the same) pictures have the same hash. This script is a great starting point for cleaning your photo library of duplicate pictures, but make sure you look at the pictures before you delete them. You have been warned! I hold no responsibility for any family memories that might be lost because of this script.

This script has only been tested with Python 3 and is still pretty rough around the edges. Use at your own risk.

## Requirements

This script requires MongoDB, Python 3.4 or higher, and a few Python modules, as found in `requirements.txt`.


## Quick Start

I suggest you read the usage, but here are the steps to get started right away. These steps assume that MongoDB is already installed on the system.

First, install this script. This can be done by either cloning the repository or [downloading the script](https://github.com/philipbl/duplicate-images/archive/master.zip).
```bash
git clone https://github.com/philipbl/duplicate-images.git
```

Next, download all required modules. This script has only been tested with Python 3. I would suggest that you make a virtual environment, setting Python 3 as the default python executable (`mkvirtualenv --python=/usr/local/bin/python3 <name>`)
```bash
pip install -r requirements.txt
```

Last, run script:
```bash
python duplicate_finder.py
```

## On Ubuntu 18.04

```bash
# Install Mongo and pip
sudo apt -y install mongodb-server python3-pip
# Disable Mongo service autostart
sudo systemctl disable mongodb.service
# Stop Mongo service
sudo service mongodb stop
```

Python 2 is the default version of Python, so we have to call `python3` explicitely:

```bash
# Install dependencies with Python 3
pip3 install -r requirements.txt
# “python duplicate_finder.py” will fail, so we have to use Python 3 for every call:
python3 duplicate_finder.py …
```

## Example

```bash

# Add your pictures to the database
# (this will take some time depending on the number of pictures)
python duplicate_finder.py add ~/Pictures
python duplicate_finder.py add /Volumes/Pictures/Originals /Volumes/Pictures/Edits

# Find duplicate images
# A webpage will come up with all of the duplicate pictures
python duplicate_finder.py find
```

## Usage

```bash
Usage:
    duplicate_finder.py add <path> ... [--db=<db_path>] [--parallel=<num_processes>]
    duplicate_finder.py remove <path> ... [--db=<db_path>]
    duplicate_finder.py clear [--db=<db_path>]
    duplicate_finder.py show [--db=<db_path>]
    duplicate_finder.py find [--print] [--delete] [--match-time] [--trash=<trash_path>] [--db=<db_path>]
    duplicate_finder.py -h | --help

Options:
    -h, --help                Show this screen

    --db=<db_path>            The location of the database or a MongoDB URI. (default: ./db)

    --parallel=<num_processes> The number of parallel processes to run to hash the image
                               files (default: number of CPUs).

    find:
        --print               Only print duplicate files rather than displaying HTML file
        --delete              Move all found duplicate pictures to the trash. This option takes priority over --print.
        --match-time          Adds the extra constraint that duplicate images must have the
                              same capture times in order to be considered.
        --trash=<trash_path>  Where files will be put when they are deleted (default: ./Trash)
```

### Add
```bash
python duplicate_finder.py add /path/to/images
```

When a path is added, image files are recursively searched for. In particular, `JPEG`, `PNG`, `GIF`, and `TIFF` images are searched for. Any image files found will be hashed. Adding a path uses 8 processes (by default) to hash images in parallel so the CPU usage is very high.

### Remove
```bash
python duplicate_finder.py remove /path/to/images
```

A path can be removed from the database. Any image inside that path will be removed from the database.

### Clear
```bash
python duplicate_finder.py clear
```

Removes all hashes from the database.

### Show
```bash
python duplicate_finder.py show
```

Prints the contents database.

### Find
```bash
duplicate_finder.py find [--print] [--delete] [--match-time] [--trash=<trash_path>]
```

Finds duplicate pictures that have been hashed. This will find images that have the same hash stored in the database. There are a few options associated with `find`. By default, when this command is run, a webpage is displayed showing duplicate pictures and a server is started that allows for the pictures to be deleted (images are not actually deleted, but moved to a trash folder -- I really don't want you to make a mistake). The first option, **`--print`**, prints all duplicate pictures and does not display a webpage or start the server. **`--delete`** automatically moves all duplicate images found to the trash. Be careful with this one. **`--match-time`** adds the extra constraint that images must have the same EXIF time stamp to be considered duplicate pictures. Last, `--trash=<trash_path>` lets you select a path to where you want files to be put when they are deleted. The default trash location is `./Trash`.

## Disclaimer

I take no responsibility for bugs in this script or accidentally deleted pictures. Use at your own risk. Make sure you back up your pictures before using.
