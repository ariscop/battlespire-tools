#!/usr/bin/env python3
from struct import unpack_from, iter_unpack

data = b''
with open(sys.argv[1], 'rb') as f:
    data = f.read()

length = unpack_from("<I", data, 0)[0]
header = data[4:length - 2]
print("Id", "Id(hex)", "Offset", "Text", sep='\t')
for offset, number in iter_unpack("<IH", header):
    print(number, hex(number), hex(offset), data[offset:data.index(0xFE, offset)], sep='\t')
