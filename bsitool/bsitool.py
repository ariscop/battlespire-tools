#!/usr/bin/env python3
import sys, base64, io
import xml.etree.ElementTree as ET
import xml.dom.minidom as md
from struct import unpack, unpack_from, iter_unpack
from pprint import pprint
from collections import defaultdict

def element(name, text=None, attrib={}):
    elem = ET.Element(name, attrib)
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
    u0, u1, width, height, u2, frames, u3, u4, u5, u6, flags = unpack("<4H6sH5H", data)
    node.append(element("width", text=width))
    node.append(element("height", text=height))
    node.append(element("frames", text=frames))
    node.append(element("u0", text=u0)) #corolation with width,
    node.append(element("u1", text=u1)) #height. aspect ratio?
    node.append(element("u2", text=to_hex(u2))) #01, 02, or 03
    node.append(element("u3", text=u3)) #values; 0 71 171 157 100 85 214 128 42 114 142 257 200 57 228
    node.append(element("u4", text=u4)) #0 or 2
    node.append(element("u5", text=u5)) #always 0
    node.append(element("u6", text=u6)) #values 256 92 115 122 174 130 153 51 76 43 56 64 163 46 110 148 156 140 112 53 120 135 125 102 97 145 99 61 38 40 58 33 74 79 35 184 158 202 143 189 171 161 117 220 197 66 151 104 138 107 207 94 186 87 243 71 235 227 84 168
    node.append(element("flags", text=flags)) #0 = uncompressed, 4 and 6 = compressed

def emit_pixel(tree, pixel):
    sys.stdout.write(tree.find(".//CMAP/colour[%d]" % (pixel + 1)).text + " ")

def parse_data_raw(tree, width, data):
    for l in iter_unpack("<%dB" % width, data):
        for c in l:
            emit_pixel(tree, c)
        print()

def parse_data_comp(tree, node, data, width, height, frames):
    height = height*frames
    for offset, comp in iter_unpack("<2H", data[:height*4]):
        node.append(element("line", attrib={"offset": str(offset), "comp": str(comp)}))
        if comp:
            f = io.BytesIO(data[offset:])
            i = 0
            while i < width:
                c = f.read(1)[0]
                if c & 0x80: #rle decompressor
                    pixel = f.read(1)[0]
                    c &= 0x7F
                    for count in range(0, c):
                        emit_pixel(tree, pixel)
                    i += c
                else:
                    for pixel in f.read(c):
                        emit_pixel(tree, pixel)
                    i += c
        else:
            for pixel in data[offset:offset+width]:
                emit_pixel(tree, pixel)
        print()


def parse_data(tree, node, data):
    flags  = int(tree.find(".//BHDR/flags").text)
    width  = int(tree.find(".//BHDR/width").text)
    height = int(tree.find(".//BHDR/height").text)
    frames = int(tree.find(".//BHDR/frames").text)

    print("P3")
    print("%d %d" % (width, height * frames))
    print("64")

    if flags == 0:
        parse_data_raw(tree, width, data)
    else:
        parse_data_comp(tree, node, data, width, height, frames)

def parse_hicl(tree, node, data):
    parse_null(tree, node, data)
    #for x in iter_unpack("B", data):
    #    node.append(element("value", text=x[0]))

def parse_htbl(tree, node, data):
    parse_null(tree, node, data)
    #for x in iter_unpack("32s", data):
    #    node.append(element("value", text=to_hex(x[0])))

def parse_cmap(tree, node, data):
    for r, g, b in iter_unpack("3B", data):
        node.append(element("colour", text="%d %d %d"% (r, g, b)))

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
    "DATA": parse_data, #variable
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
        node = ET.Element(name, {"_length": str(length)})
        parsers[name](tree, node, childdata)
        bsif.append(node)
    return bsif

data = b''
with open(sys.argv[1], "rb") as fd:
    data = fd.read()

root = ET.Element("BSIF", {"_length": str(len(data))})
tree = ET.ElementTree(root)
readGroup(tree, root, data)

#print(ET.tostring(node))
#print(md.parseString(ET.tostring(root)).toprettyxml())
