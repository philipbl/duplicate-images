import concurrent.futures
import os

import imagehash
import magic
from PIL import Image, ExifTags


def hash_file(file):
    try:
        hashes = []
        img = Image.open(file)

        file_size = get_file_size(file)
        image_size = get_image_size(img)
        capture_time = get_capture_time(img)

        # 0 degree hash
        hashes.append(str(imagehash.phash(img)))

        # 90 degree hash
        img = img.rotate(90, expand=True)
        hashes.append(str(imagehash.phash(img)))

        # 180 degree hash
        img = img.rotate(90, expand=True)
        hashes.append(str(imagehash.phash(img)))

        # 270 degree hash
        img = img.rotate(90, expand=True)
        hashes.append(str(imagehash.phash(img)))

        hashes = ''.join(sorted(hashes))

        result = {'file_name': file,
                  'hash': hashes,
                  'file_size': file_size,
                  'image_size': image_size,
                  'capture_time': capture_time}
        return file, result

    except OSError:
        return file, None


def hash_files(files, processes):
    if processes == 1:
        # If only one process is going to be used, don't bother making a process pool
        yield from (hash_file(file) for file in files)

    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=processes) as executor:
            yield from executor.map(hash_file, files)


def get_image_files(path):
    """
    Check path recursively for files. If any compatible file is found, it is
    yielded with its full path.

    :param path:
    :return: yield absolute path
    """
    def is_image(file_name):
        # List mime types fully supported by Pillow
        full_supported_formats = ['gif', 'jp2', 'jpeg', 'pcx', 'png', 'tiff', 'x-ms-bmp',
                                  'x-portable-pixmap', 'x-xbitmap']
        try:
            mime = magic.from_file(file_name, mime=True)
            return mime.rsplit('/', 1)[1] in full_supported_formats
        except IndexError:
            return False

    path = os.path.abspath(path)
    for root, dirs, files in os.walk(path):
        for file in files:
            file = os.path.join(root, file)
            if is_image(file):
                yield file


def get_file_size(file_name):
    try:
        return os.path.getsize(file_name)
    except FileNotFoundError:
        return 0


def get_image_size(img):
    return "{} x {}".format(*img.size)


def get_capture_time(img):
    try:
        exif = {
            ExifTags.TAGS[k]: v
            for k, v in img._getexif().items()
            if k in ExifTags.TAGS
        }
        return exif["DateTimeOriginal"]
    except:
        return "Time unknown"


def delete_image(file_name, trash):
    shutil.move(file_name, os.path.join(trash, os.path.basename(file_name)))
