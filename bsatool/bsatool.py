#!/usr/bin/env python3
import sys, os
from io import BytesIO
from array import array
from struct import calcsize, unpack_from, iter_unpack

with open(sys.argv[1], "rb") as fd:
    data = memoryview(fd.read())

def bits(byte):
    return ((byte >> 0) & 1,
            (byte >> 1) & 1,
            (byte >> 2) & 1,
            (byte >> 3) & 1,
            (byte >> 4) & 1,
            (byte >> 5) & 1,
            (byte >> 6) & 1,
            (byte >> 7) & 1)

def decompress(fd):
    window = array('B', (b' ' * 4078) + (b'\x00' * 18))

    pos = 4078
    _out = BytesIO()

    def out(byte):
        nonlocal window, pos
        window[pos] = byte
        pos = (pos + 1) & 0xFFF
        _out.write(bytes([byte]))

    try:
        while True:
            for encoded in bits(fd.read(1)[0]):
                if encoded:
                    out(fd.read(1)[0])
                else: #encoded
                    code = fd.read(2)
                    offset = code[0] | (code[1] & 0xF0) << 4
                    length = (code[1] & 0xF) + 3

                    for x in range(offset, offset+length):
                        out(window[x & 0xFFF])
    except IndexError:
        pass

    return _out.getbuffer()


recordCount, recordType = unpack_from("<2H", data, 0)

print("Offset", "Length", "Compressed", "Name", sep='\t')

offset = 4
struct_fmt = "<12sHI"

if recordType == 0x200:
    struct_fmt = "<2HI"
elif recordType != 0x100:
    offset = 2

footer = data[len(data) - (recordCount * calcsize(struct_fmt)):]

for name, compressed, size in iter_unpack(struct_fmt, footer):
    if isinstance(name, bytes):
        name = name.decode().rstrip('\x00')
    print(hex(offset), size, hex(compressed), str(name), sep='\t')
    if len(sys.argv) > 2:
        path = os.path.join(sys.argv[2], str(name))
        filedata = data[offset:offset+size]
        if compressed:
            filedata = decompress(BytesIO(filedata))
        with open(path, 'wb') as out:
            out.write(filedata)
    offset += size
