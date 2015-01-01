#!/usr/bin/env python3
import sys, base64
import xml.etree.ElementTree as ET
import xml.dom.minidom as md
from struct import unpack, unpack_from, iter_unpack
from pprint import pprint
from collections import defaultdict

data = b''
with open(sys.argv[1], "rb") as fd:
    data = fd.read()

def parse_string(name, node, data):
    node.text = data[0:data.index(0)].decode()

def parse_dirn(name, node, data):
    node.text = data[0:data.index(0)].decode()
    data = data[data.index(0):]
    #whoever wrote the DIRN exporter doesn't memset() first
    #perhaps interesting leak in 260 byte blobs?
    #with open("/tmp/leaklog", "ab") as leaklog:
    #   leaklog.write(data)

def parse_int32(name, node, data):
    node.text = str(unpack("<I", data)[0])

def parse_6int32(name, node, data):
    x, y, z, x2, y2, z2 = unpack("<6I", data)
    pos = {"x": (x,x2), "y": (y,y2), "z": (z,z2)}
    for k, v in pos.items():
        e = ET.Element(k)
        e.text = str(v)
        node.append(e)

def parse_pos(name, node, data):
    x, y, z = unpack("<3I", data)
    pos = {"x": x, "y": y, "z": z}
    for k, v in pos.items():
        e = ET.Element(k)
        e.text = str(v)
        node.append(e)

def parse_lfil(name, node, data):
    names = [x for x in iter_unpack("260s", data)]
    for name in (name[0].decode().strip('\x00') for name in names):
        child = ET.Element("name")
        child.text = name
        node.append(child)

def parse_raw(name, node, data):
    node.text = base64.b64encode(data).decode()

def parse_group(name, node, data):
    for child in readGroup(data):
        node.append(child)

parsers = {
    "FILN": parse_string,
    "DIRN": parse_dirn,
    "RADI": parse_int32,
    "IDNB": parse_int32,
    "IDTY": parse_int32,
    "BRIT": parse_int32,
    "SELE": parse_int32,
    "SCAL": parse_int32,
    "AMBI": parse_int32,
    "IDFI": parse_int32,
    "BITS": parse_int32,
    "WATR": parse_int32,
    "BBOX": parse_6int32,
    "POSI": parse_pos,
    "OFST": parse_pos,
    "CENT": parse_pos,
    "ANGS": parse_pos,
    "LFIL": parse_lfil,
    "RAWD": parse_raw,
    "GNRL": parse_group,
    "TEXI": parse_group,
    "STRU": parse_group,
    "SNAP": parse_group,
    "VIEW": parse_group,
    "CTRL": parse_group,
    "LINK": parse_group,
    "OBJS": parse_group,
    "OBJD": parse_group,
    "LITS": parse_group,
    "LITD": parse_group,
    "FLAS": parse_group,
    "FLAD": parse_group,
}


def blocks(data):
    while len(data) > 8:
        name, length = unpack_from('<4sI', data, 0)
        childdata = data[8:8+length]
        yield (name.decode(), length, childdata)
        data = data[8+length:]

def readGroup(data):
    for name, length, childdata in blocks(data):
        node = ET.Element(name, {"_length": str(length)})
        parsers[name](name, node, childdata)
        yield node

node = [x for x in readGroup(data)][0]
#print(ET.tostring(node))
print(md.parseString(ET.tostring(node)).toprettyxml())
