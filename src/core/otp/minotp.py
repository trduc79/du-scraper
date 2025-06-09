"""

The MIT License (MIT)
=====================

Copyright (c) 2019 Susam Pal https://github.com/susam/mintotp
Copyright (c) 2022 Jak Wings https://github.com/jakwings/totp

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import base64
import hmac
import struct
import sys
import time


def hotp(key: str, counter: int, digits=6, digest="sha1") -> str:
    """Return HOTP"""
    key = base64.b32decode(key.upper() + "=" * ((8 - len(key)) % 8))  # type: ignore
    counter = struct.pack(">Q", counter)  # type: ignore
    mac = hmac.new(key, counter, digest).digest()  # type: ignore
    offset = mac[-1] & 0x0F
    binary = struct.unpack(">L", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary)[-digits:].zfill(digits)  # type: ignore


def totp(key: str, time_step=30, digits=6, digest="sha1") -> str:
    """Return TOTP"""
    time_stamp = time.time()
    otp = hotp(key, int(time_stamp / time_step), digits, digest)
    return otp


def test_main():
    """Test functionality"""
    args = [int(x) if x.isdigit() else x for x in sys.argv[1:]]
    for key in sys.stdin:
        print(totp(key.strip(), *args))  # type: ignore


if __name__ == "__main__":
    test_main()
