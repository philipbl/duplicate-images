"""Image perceptive hasher"""
import binascii
import imagehash
from PIL import Image, ExifTags
from pillow_heif import register_heif_opener
from . import abstracthasher

register_heif_opener()


class ImageHasher(abstracthasher.AbstractHasher):
    """Image perceptive hasher"""
    def is_applicable(self, file_name: str) -> bool:
        return self._is_matching_magic(
            file_name,
            ['gif', 'jp2', 'jpeg', 'pcx', 'png', 'tiff', 'x-ms-bmp',
             'x-portable-pixmap', 'x-xbitmap', 'heic']
        )

    def _get_capture_time(self, img):
        try:
            exif = {
                ExifTags.TAGS[k]: v
                for k, v in img.getexif().items()
                if k in ExifTags.TAGS
            }
            return exif["DateTimeOriginal"]
        except:
            return "Time unknown"

    def hash(self, file_object) -> tuple:
        img = Image.open(file_object)

        hashes = []
        # hash the image 4 times and rotate it by 90 degrees each time
        for angle in [0, 90, 180, 270]:
            if angle > 0:
                turned_img = img.rotate(angle, expand=True)
            else:
                turned_img = img
            hashes.append(
                b'img:' +
                binascii.unhexlify(str(imagehash.phash(turned_img)))
            )

        return (
            hashes,
            {
                'image_size': f'{img.size[0]} x {img.size[1]}',
                'capture_time': self._get_capture_time(img)
            }
        )
