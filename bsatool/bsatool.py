#!/usr/bin/env python3
import sys, os
from struct import calcsize, unpack_from, iter_unpack

with open(sys.argv[1], "rb") as fd:
    data = memoryview(fd.read())

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
        with open(path, 'wb') as out:
            out.write(data[offset:offset+size])
    offset += size
