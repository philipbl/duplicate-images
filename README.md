# Duplicate Image Finder

This Python script finds duplicate images using a [perspective hash (pHash)](http://www.phash.org) to compare images. pHash ignores the image size and file size and instead creates a hash based on the pixels of the image. This allows you to find duplicate pictures that have been rotated, have changed metadata, and edited.

This script hashes images added to it, storing the hash into a database. To find duplicate images, hashes are compared. If the hash is the same between two images, then they are marked as duplicates. A web interface is provided to delete duplicate images easily. If you are feeling lucky, there is an option to automatically delete duplicate files.

As a word of caution, pHash is not perfect. I have found that duplicate pictures sometimes have different hashes and similar (but not the same) pictures have the same hash. This script is a great starting point for cleaning your photo library of duplicate pictures, but make sure you look at the pictures before you delete them. You have been warned! I hold no responsibility for any family memories that might be lost because of this script.

This script has only been tested with Python 3 and is still pretty rough around the edges. Use at your own risk.

## Quick Start

I suggest you read the usage, but here are the steps to get started right away. These steps assume that Mongodb is already installed on the system.

First, install this script. This can be done by either cloning the repository or [downloading the script](https://github.com/philipbl/duplicate-images/archive/master.zip).
```
git clone https://github.com/philipbl/duplicate-images.git
```

Next, download all required modules. This script has only been tested with Python 3. I would suggest that you make a virtual environment, setting Python 3 as the default python executable (`mkvirtualenv --python=/usr/local/bin/python3 <name>`)
```
pip install -r requirements.txt
```

Last, run script:
```
python duplicate_finder.py
```


## Usage

```
Usage:
    duplicate_finder.py add <path> ... [--db=<db_path>] [--parallel=<num_processes>]
    duplicate_finder.py remove <path> ... [--db=<db_path>]
    duplicate_finder.py clear [--db=<db_path>]
    duplicate_finder.py show [--db=<db_path>]
    duplicate_finder.py find [--print] [--match-time] [--trash=<trash_path>] [--db=<db_path>]
    duplicate_finder.py dedup [--confirm] [--match-time] [--trash=<trash_path>]
    duplicate_finder.py -h | –-help

Options:
    -h, -–help                Show this screen

    --db=<db_path>            The location of the database. (default: ./db)

    --parallel=<num_processes> The number of parallel processes to run to hash the image
                               files (default: 8).

    find:
        --print               Only print duplicate files rather than displaying HTML file
        --match-time          Adds the extra constraint that duplicate images must have the
                              same capture times in order to be considered.
        --trash=<trash_path>  Where files will be put when they are deleted (default: ./Trash)

     dedup:
        --confirm             Confirm you realize this will delete duplicates automatically.
```

### Add
```
python duplicate_finder.py add /path/to/images
```

When a path is added, image files are recursively searched for. In particular, `JPEG`, `PNG`, `GIF`, and `TIFF` images are searched for. Any image files found will be hashed. Adding a path uses 8 processes (by default) to hash images in parallel so the CPU usage is very high.

### Remove
```
python duplicate_finder.py remove /path/to/images
```

A path can be removed from the database. Any image inside that path will be removed from the database.

### Clear
```
python duplicate_finder.py clear
```

Removes all hashes from the database.

### Show
```
python duplicate_finder.py show
```

Prints the contents database.

### Find
```
python duplicate_finder.py find [--print] [--match-time] [--trash=<trash_path>]
```

Finds duplicate pictures that have been hashed. This will find images that have the same hash stored in the database. There are a few options associated with `find`. By default, when this command is run, a webpage is displayed showing duplicate pictures and a server is started that allows for the pictures to be deleted (images are not actually deleted, but moved to a trash folder -- I really don't want you to make a mistake). The first option, `--print`, prints all duplicate pictures and does not display a webpage or start the server. `--match-time` adds the extra constraint that images must have the same EXIF time stamp to be considered duplicate pictures. Last, `--trash=<trash_path>` lets you select a path to where you want files to be put when they are deleted. The trash path must already exist before a image is deleted.

### Dedup
```
python duplicate_finder.py dedup [--confirm] [--match-time] [--trash=<trash_path>]
```

Similar to find, except that it deletes any duplicate picture it finds rather than bringing up a webpage. To make sure you really want to do this, you must provide the `--confirm` flag. See `find` for a description of the other options.

## Requirements

This script requires Mongodb and a few python modules, as found in `requirements.txt`.


## Disclaimer

I take no responsibility for bugs in this script or accidentally deleted pictures. Use at your own risk. Make sure you back up your pictures before using.
