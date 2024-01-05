"""Video hasher"""
import datetime
import av
from PIL import Image
import numpy as np

from . import videohasher, abstracthasher


class VideoBarcodeHasher(videohasher.VideoHasher):
    """Video Barcode hasher
    https://pyav.org/docs/develop/cookbook/numpy.html#video-barcode"""

    def __init__(self, image_hasher: abstracthasher.AbstractHasher):
        super(VideoBarcodeHasher).__init__(self, image_hasher)

    def hash(self, file_object) -> tuple:
        hashes = []
        duration = 0
        frames = 0
        columns = []
        with av.open(file_object) as video_decoder:
            stream = video_decoder.streams.video[0]
            stream.codec_context.skip_frame = "NONKEY"

            for frame in video_decoder.decode(video=0):
                array = frame.to_ndarray(format="rgb24")
                # Collapse down to a column.
                column = array.mean(axis=1)
                # Convert to bytes, as the `mean` turned our array into floats.
                column = column.clip(0, 255).astype("uint8")
                # Get us in the right shape for the `hstack` below.
                column = column.reshape(-1, 1, 3)
                columns.append(column)

            if stream.duration is not None:
                duration = float(stream.duration * stream.time_base)
            frames = stream.frames

        full_array = np.hstack(columns)
        full_img = Image.fromarray(full_array, "RGB")
        ih = self._image_hasher.hash(full_img)
        hashes = hashes + ih[0]

        hashes = list(set(hashes))  # make hashes unique
        return self._format_hashes(hashes, frames, str(datetime.timedelta(seconds=duration)))
