"""
Parses a websocket connection.

Yields a response object followed by 0 or more Websocket messages.

"""

from __future__ import unicode_literals

import logging

from six import text_type

from . import errors
from .frame import CompressedFrame, Frame
from .frame_parser import CompressedFrameParser, FrameParser
from .header_parser import HeaderParser
from .message import Message
from .parser import ParseError
from .response import Response


log = logging.getLogger('lomond')


class WebsocketStream(object):
    """
    Parses a stream of data in to Headers and logical Websocket
    frames.

    """

    def __init__(self):
        self.header_parser = HeaderParser()
        self.frame_parser = FrameParser()
        self._parsed_response = False
        self._frames = []
        self._compression = None

    def set_compression(self, compression):
        """Set a compression object for decompressing messages."""
        self.frame_parser = CompressedFrameParser()
        self._compression = compression

    def build_message(self, frames):
        """Return a message, built from a list of frames."""
        return Message.build(frames, self._compression.decompress)

    def feed(self, data):
        """Feed in data from a socket to yield 0 or more frames."""
        # This combines fragmented frames in to a single frame

        if not self._parsed_response:
            header_data = next(self.header_parser.feed(data))
            if header_data is not None:
                yield Response(header_data)
                self._parsed_response = True
            data = self.header_parser.unparsed_data
            if not data:
                return

        iter_frames = iter(self.frame_parser.feed(data))

        # Process incoming frames
        while True:
            try:
                frame = next(iter_frames)
            except ParseError as error:
                raise errors.CriticalProtocolError(
                    text_type(error)
                )
            log.debug(" SRV -> CLI : %r", frame)
            if frame.is_control:
                # Control messages are never fragmented
                # And may be sent in the middle of a multi-part message
                yield self.build_message([frame])
            else:
                # May be fragmented
                if frame.is_continuation and not self._frames:
                    raise errors.ProtocolError(
                        'continuation frame has nothing to continue'
                    )
                if not frame.is_continuation and self._frames:
                    raise errors.ProtocolError(
                        'continuation frame expected'
                    )
                self._frames.append(frame)
                if frame.fin:
                    yield self.build_message(self._frames)
                    del self._frames[:]
