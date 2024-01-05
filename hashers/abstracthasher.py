"""Interface class of all hashers"""
from abc import ABC, abstractmethod
import magic


class AbstractHasher(ABC):
    """Interface class of all hashers, implements basic functions"""

    def is_applicable(self, _: str) -> bool:
        """Return if the hasher is applicable, must be overwritten in the
        child."""
        return False

    @abstractmethod
    def hash(self, file_object) -> tuple:
        """Hash file"""

    def _is_matching_magic(self, file_name: str, supported_magics: list) \
            -> bool:
        try:
            mime = magic.from_file(file_name, mime=True)
            return mime.rsplit('/', 1)[1] in supported_magics
        except IndexError:
            return False
