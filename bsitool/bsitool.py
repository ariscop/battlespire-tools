#!/usr/bin/env python3
import sys, base64, io
import xml.etree.ElementTree as ET
import xml.dom.minidom as md
from PIL import Image
from struct import unpack, unpack_from, iter_unpack
from pprint import pprint
from collections import defaultdict, namedtuple

def unpack_15bpp(pixel):
    return (
        (8 * (pixel & 0b0111110000000000) >> 10),
        (8 * (pixel & 0b0000001111100000) >> 5),
        (8 * (pixel & 0b0000000000011111) >> 0)
    )

class DataElement(ET.Element):
    def __init__(self, tag, attrib={}):
        ET.Element.__init__(self, tag, attrib=attrib)
        self.data = None

    def __setattr__(self, name, value):
        if name is "data":
            self.__dict__["data"] = value
        else:
            ET.Element.__setattr__(self, name, value)

    def __getattr__(self, name):
        if name is "data":
            return self.__dict__["data"]
        else:
            return ET.Element.__getattr__(self, name)

def element(name, attrib={}, text=None):
    elem = DataElement(name, attrib)
    if not text is None:
        elem.text = str(text)
    return elem

def parse_null(tree, node, data):
    pass

def to_hex(string):
    return ''.join(format(x, '02x') for x in string)

def parse_hex(tree, node, data):
    node.text = to_hex(data)

def parse_string(tree, node, data):
    node.text = data[0:data.index(0)].decode()

def parse_ifhd(tree, node, data):
    node.text = to_hex(data.rstrip(b'\x00'))

def parse_bhdr(tree, node, data):
    u0, u1, width, height, u2, frames, u3, u4, u5, u6, flags = unpack("<4H6s6H", data)
    node.append(element("width", text=width))
    node.append(element("height", text=height))
    node.append(element("frames", text=frames))
    node.append(element("u0", text=u0)) #corolation with width,
    node.append(element("u1", text=u1)) #some kind of offset
    node.append(element("u2", text=to_hex(u2))) #01, 02, or 03
    node.append(element("u3", text=u3)) #values; 0 71 171 157 100 85 214 128 42 114 142 257 200 57 228
    node.append(element("u4", text=u4)) #0 or 2
    node.append(element("u5", text=u5)) #always 0
    node.append(element("u6", text=u6)) #values 256 92 115 122 174 130 153 51 76 43 56 64 163 46 110 148 156 140 112 53 120 135 125 102 97 145 99 61 38 40 58 33 74 79 35 184 158 202 143 189 171 161 117 220 197 66 151 104 138 107 207 94 186 87 243 71 235 227 84 168
    node.append(element("flags", text=flags)) #0 = uncompressed, 4 and 6 = compressed

def parse_cmap(tree, node, data):
    i = -1
    for g, b, r in iter_unpack("3B", data):
        i += 1
        if r == g == b == 0:
            continue
        node.append(element("colour", text="%d %d %d" % (r, g, b), attrib={"id": str(i)}))

def parse_hicl(tree, node, data):
    i = -1
    for x in iter_unpack(">H", data):
        i += 1
        r, g, b = unpack_15bpp(x[0])
        if r == g == b == 0:
            continue
        node.append(element("colour", text="%d %d %d" % (r, g, b), attrib={"id": str(i)}))

def parse_htbl(tree, node, data):
    i = -1
    res = []
    for x in iter_unpack("256s", data):
        i += 1
        node.append(element("unknown", text=to_hex(x[0]), attrib={"id": str(i)}))
        res.append(x[0])
    node.data = res

def parse_unknown(tree, node, data):
    sys.stderr.write("Unknown block type: %s\n" % node.tag)
    parse_raw(tree, node, data)

def constant_factory(value):
    return lambda: value
parsers = defaultdict(constant_factory(parse_unknown))

parsers.update({
    "IFHD": parse_ifhd, #44 bytes fixed
    "BHDR": parse_bhdr, #26 bytes fixed
    "NAME": parse_string, #variable
    "DATA": parse_null, #variable
    "HICL": parse_hicl, #256 fixed
    "HTBL": parse_htbl, #8192 fixed
    "CMAP": parse_cmap, #768 fixed #parse_cmap
    "END ": parse_null,
})


def blocks(data):
    while len(data) >= 8:
        name, length = unpack_from('>4sI', data, 0)
        childdata = data[8:8+length]
        yield (name.decode(), length, childdata)
        data = data[8+length:]

def readGroup(tree, bsif, data):
    # Battlespires engine does the same
    if b'BSIF' == unpack_from('>4s', data, 0)[0]:
        data = data[8:]

    for name, length, childdata in blocks(data):
        node = element(name, {"_length": str(length)})
        node.data = childdata
        parsers[name](tree, node, childdata)
        bsif.append(node)
    return bsif

data = b''
with open(sys.argv[1], "rb") as fd:
    data = fd.read()

root = ET.Element("BSIF", {"_length": str(len(data))})
tree = ET.ElementTree(root)
readGroup(tree, root, data)

xml = md.parseString(ET.tostring(root)).toprettyxml()
if len(sys.argv) > 3:
    with open(sys.argv[3], "w") as fd:
        fd.write(xml)
else:
    print(xml)

if len(sys.argv) < 3:
    exit()

flags  = int(tree.find(".//BHDR/flags").text)
width  = int(tree.find(".//BHDR/width").text)
height = int(tree.find(".//BHDR/height").text)
frames = int(tree.find(".//BHDR/frames").text)
cmap = tree.find(".//CMAP").data
data = tree.find(".//DATA").data
hicl = tree.find(".//HICL").data
htbl = tree.find(".//HTBL")

def decomp(data, width, height):
    out = []
    for offset, comp in iter_unpack("<3sB", data[:height*4]):
        offset = int.from_bytes(offset, 'little')
        if comp == 0x80: #rle compression
            f = io.BytesIO(data[offset:])
            i = 0
            while i < width:
                c = f.read(1)[0]
                if c & 0x80:
                    pixel = f.read(1)[0]
                    c &= 0x7F
                    for count in range(0, c):
                        out.append(pixel)
                    i += c
                else:
                    for pixel in f.read(c):
                        out.append(pixel)
                    i += c
        elif comp == 0:
            [out.append(x) for x in data[offset:offset+width]]
        else:
            raise Exception("Unknown compression %s", hex(comp))
    return(bytes(out))


if flags != 0:
    data = decomp(data, width, height * frames)

data = [x & 0x7F for x in data] #how to handle values over 127?

def bpp15_to_rgb(data):
    ret = []
    for x in unpack("<128H", data):
        for y in unpack_15bpp(x):
            ret.append(y)
    return ret

palettes = dict()

if htbl:
    for x in range(0, 32):
        palettes["htbl-%2d" % x] = bpp15_to_rgb(htbl.data[x])

palettes["hicl"] = bpp15_to_rgb(hicl)
palettes["cmap"] = [x * 4 for x in cmap]

out = Image.new("P", (width, height * frames))
out.putdata(data)

for name, palette in palettes.items():
    out.putpalette(palette)
    out.save(sys.argv[2] % name)

exit(0)

palette = bpp15_to_rgb(hicl)
#palette = [x*4 for x in cmap]
#palette = []
#for x in iter_unpack("<H", hicl):
#    x = x[0]
#    palette.append(4 * (x & 0b0111110000000000) >> 10)
#    palette.append(4 * (x & 0b0000001111100000) >> 5)
#    palette.append(4 * (x & 0b0000000000011111) >> 0)


#alpha = [0 if x == 0 else 1 for x in data]

out = Image.new("P", (width, height * frames))
out.putpalette(palette)
out.putdata(data)

#pil sucks
#out = out.convert(mode="RGBA")
#alphalayer = Image.new("1", (width, height * frames))
#alphalayer.putdata(alpha)
#out.putalpha(alphalayer)
out.save(sys.argv[2])
