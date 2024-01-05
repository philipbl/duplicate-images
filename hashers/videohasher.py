"""Video hasher"""
import datetime
import av
from . import abstracthasher


class VideoHasher(abstracthasher.AbstractHasher):
    """Video hasher"""

    def __init__(self, image_hasher: abstracthasher.AbstractHasher,
                 frames_number=5):
        self._image_hasher = image_hasher
        self._frames_number = frames_number

    def is_applicable(self, file_name: str) -> bool:
        return self._is_matching_magic(
            file_name,
            ['x-matroska', 'MP2T', 'mp4', 'ogg', 'x-msvideo',
             'webm', 'quicktime']
        )

    def hash(self, file_object) -> tuple:
        hashes = []
        duration = 0
        frames = 0
        with av.open(file_object, mode='r') as video_decoder:
            stream = video_decoder.streams.video[0]
            stream.codec_context.skip_frame = "NONKEY"
            video_duration = video_decoder.duration
            fraction = video_duration // self._frames_number
            for i in range(self._frames_number):
                seek_position = i * fraction + (fraction // 2)
                # seek to position but shifted half of the fraction back
                try:
                    video_decoder.seek(seek_position)
                    for frame in video_decoder.decode():
                        if isinstance(frame, av.video.frame.VideoFrame):
                            ih = self._image_hasher.hash(frame.to_image())
                            hashes = hashes + ih[0]
                            break
                except av.error.PermissionError:
                    pass

            if stream.duration is not None:
                duration = float(stream.duration * stream.time_base)
            frames = stream.frames

        hashes = list(set(hashes))  # make hashes unique
        return self._format_hashes(hashes, frames, str(datetime.timedelta(seconds=duration)))

    def _format_hashes(self, hashes, frames, duration):
        return (
            hashes,
            {
                'total_frames': frames,
                'duration': duration,
            }
        )
