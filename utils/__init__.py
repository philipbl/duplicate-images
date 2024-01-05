"""Pretty progress printer with internal counter and ETA estimation."""
import datetime
from termcolor import cprint


class ProgressBarPrinter():
    """Progress bar printer."""

    def __init__(self, _max):
        self._max = _max
        self._start_time = None
        self.reset()

    def print(self):
        """Print progress"""
        cprint(f' {round(self._current * 100 / (self._max - 1))}%', end='')
        if self._start_time is not None:
            duration = datetime.datetime.now() - self._start_time
            left = duration * (self._max - self._current) / self._current
            left = left - datetime.timedelta(microseconds=left.microseconds)

            eta = datetime.datetime.now() + left
            eta = eta - datetime.timedelta(microseconds=eta.microsecond)

            cprint(f' finishing in {str(left)} seconds at {eta}\r', end='')
        else:
            cprint('                                          \r', end='')

        return self

    def inc(self):
        """Increment progress"""
        self._current += 1
        if self._start_time is None:
            self._start_time = datetime.datetime.now()
        return self

    def reset(self):
        """Reset progress"""
        self._current = 0
        self._start_time = None
        return self
