"""
Functions related to masking Websocket frames.
https://tools.ietf.org/html/rfc6455#section-5.3

# TODO: Use wsaccel for masking

"""

import os
from functools import partial
from itertools import izip, cycle

import six


make_masking_key = partial(os.urandom, 4)


if six.PY2:
    def mask(masking_key, data):
        return b''.join(
            chr(ord(a) ^ ord(b))
            for a, b in izip(cycle(masking_key), data)
        )
else:
    # Can't deny the Py3 version is nicer
    def mask(masking_key, data):
        return bytes(a ^ b for a, b in izip(cycle(masking_key), data))
