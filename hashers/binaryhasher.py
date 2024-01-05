"""Binary hasher"""
from hashlib import blake2b
from . import abstracthasher

BINARY_HASHER_BLOCK_SIZE = 65536


class BinaryHasher(abstracthasher.AbstractHasher):
    """Binary hasher: uses blake2b to hash all binary data"""
    def __init__(self, digest_size=None):
        self._digest_size = digest_size if digest_size is not None else 16

    def is_applicable(self, _: str) -> bool:
        return True

    def hash(self, file_object) -> tuple:
        hasher = blake2b(digest_size=self._digest_size)
        while True:
            data = file_object.read(BINARY_HASHER_BLOCK_SIZE)
            if not data:
                break
            hasher.update(data)

        return (
            [
                b'bin:' + hasher.digest()
            ],
            {
                'file_size': file_object.tell()
            }
        )
