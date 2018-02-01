# Duplicate Image Finder

## Quick Start

I suggest you read the usage, but here are the steps to get started right away. These steps assume that you have SQLite already installed on the system.

```
# Install script
pip install duplicate_finder

# Process images in given paths (could take a long time)
duplicate_finder add_paths folder/to/your/pictures

# Find duplicates! A webpage should pop up with all of the duplicate images it found.
duplicate_finder find
```

## Description

This Python script finds duplicate images using a [perspective hash (pHash)](http://www.phash.org) to compare images. pHash ignores the image size and file size and instead creates a hash based on the pixels of the image. This allows you to find duplicate pictures that have been rotated, have changed metadata, and slightly edited.

This script hashes images added to it, storing the hash into a database. To find duplicate images, hashes are compared. If the hash is the same between images, then they are marked as duplicates. A web interface is provided to delete duplicate images easily. If you are feeling lucky, there is an option to automatically delete duplicate files.

As a word of caution, pHash is not perfect. I have found that duplicate pictures sometimes have different hashes and similar (but not the same) pictures have the same hash. This script is a great starting point for cleaning your photo library of duplicate pictures, but make sure you look at the pictures before you delete them. You have been warned! I hold no responsibility for any personal or family memories that might be lost because of this script.

This script has only been tested with Python 3.4+. Use at your own risk.

## Requirements

This script requires a database. The supported databases are [TinyDB](http://tinydb.readthedocs.io/en/latest/), [MongoDB](https://www.mongodb.com), and [SQLite](https://www.sqlite.org). The default database is SQLite.  TinyDB is the lightest database and requires no external dependencies, but the performance is not great (see Performance section). To use SQLite, it must be installed on your computer. To use MongoDB, MongoDB must be running before you run this script.


## Example

```bash

# Add your pictures to the database
# (this will take some time depending on the number of pictures)
duplicate_finder add_paths ~/Pictures
duplicate_finder add_paths /Volumes/Pictures/Originals /Volumes/Pictures/Edits

# Find duplicate images
# A webpage will come up with all of the duplicate pictures
duplicate_finder find
```

## Usage

```bash
Usage: duplicate_finder [OPTIONS] COMMAND [ARGS]...

Options:
  --version                     Show the version and exit.
  --db [mongodb|sqlite|tinydb]  [default: tinydb]
  --db-location TEXT            The location of the database. This will change
                                depending on the database used. [defaults
                                mongodb: mongodb://localhost:27017, sqlite:
                                ./db.sqlite, tinydb: ./db.json]
  --help                        Show this message and exit.

Commands:
  add_path     Processes all images in given path(s), adding them to the
               database.
  clear_db     Clears database.
  find         Searches database for duplicate images.
  remove_path  Removes all images information in the given path(s) from
               database.
  show_db      Prints out all image information stored in database.
```

### Selecting a Database

```bash
duplicate_finder --db [mongodb|sqlite|tinydb] --db-location TEXT
```

`duplicate_finder` uses a database to store all of the image hashes and find duplicate images quickly. Currently, you have three options (PRs welcome for support for other DBs!): MongoDB, SQLite, and TinyDB. Depending on which database you select, you might need to provide a database location. The defaults are as follows:

```
MongoDB:   mongodb://localhost:27017
SQLite:    ./db.sqlite
TinyDB:    ./db.json
```

For example, if you want to connect to a remote MongoDB instance, you would run:

```bash
duplicate_finder --db mongodb --db-location mongodb://username:password@test.com:27017 ...
```

If you have another location for your SQLite database, you would run:

```bash
duplicate_finder --db sqlite --db-location /home/user/image_data.sqlite ...
```

### Add Paths
```bash
duplicate_finder add_paths /path/to/images ... [--parallel INT]
```

When a path is added, image files are recursively searched for. In particular, files with `gif`, `jp2`, `jpeg`, `pcx`, `png`, `tiff`, `x-ms-bmp`, `x-portable-pixmap`, and `x-xbitmap` mime types are considered images. Any image files found will be hashed. Adding a path uses all of the cores on your computer to hash images in parallel so the CPU usage is very high. This can be changed with the `--parallel` option.

### Find
```bash
duplicate_finder find [--print] [--delete] [--match-time] [--trash=<trash_path>]
```

Finds duplicate pictures that have been hashed. This will find images that have the same hash stored in the database. There are a few options associated with `find`. By default, when this command is run, a webpage is displayed showing duplicate pictures and a server is started that allows for the pictures to be deleted (images are not actually deleted, but moved to a trash folder -- I really don't want you to make a mistake). The first option, **`--print`**, prints all duplicate pictures and does not display the webpage or start the server. **`--delete`** automatically moves all duplicate images found to the trash. Be careful with this one. **`--match-time`** adds the extra constraint that images must have the same EXIF time stamp to be considered duplicate pictures. Last, **`--trash=<trash_path>`** lets you select a path to where you want files to be put when they are deleted. The default trash location is `./Trash`. The speed of `find` will depend on which database you selected and how many pictures you have added.

### Remove Paths
```bash
duplicate_finder remove_paths /path/to/images ...
```

When a path is removed, image files are recursively searched for and removed __from the database__ -- your pictures are not touched. You probably won't need this option very often.


### Clear
```bash
duplicate_finder clear_db
```

Removes all hashes from the database.

### Show
```bash
duplicate_finder show
```

Prints the contents database.


## Performance


## Disclaimer

I take no responsibility for bugs in this script or accidentally deleted pictures. Use at your own risk. Make sure you back up your pictures before using.
