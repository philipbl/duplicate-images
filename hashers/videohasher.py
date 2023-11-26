"""Video hasher"""
from . import abstracthasher


class VideoHasher(abstracthasher.AbstractHasher):
    """Video hasher"""

    def __init__(self, image_hasher: abstracthasher.AbstractHasher):
        self._image_hesher = image_hasher

    def is_applicable(self, file_name: str) -> bool:
        return self._is_matching_magic(
            file_name,
            []
        )

    def hash(self, file_object) -> tuple:
        return (
            [],
            {}
        )
