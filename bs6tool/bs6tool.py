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

#these bocks contain other blocks
groups = [
     "GNRL"
    ,"TEXI"
    ,"STRU"
    ,"SNAP"
    ,"VIEW"
    ,"CTRL"
    ,"LINK"
    ,"OBJS"
    ,"OBJD"
    ,"LITS"
    ,"LITD"
    ,"FLAS"
    ,"FLAD"
]

unknown = set()

def parse_unknown(name, node, data):
    if name in groups:
        return
    unknown.add(name)
    node.text = base64.b64encode(data).decode()

def constant_factory(value):
     return lambda: value

parsers = defaultdict(constant_factory(parse_unknown))

def parse_string(name, node, data):
    node.text = data[0:data.index(0)].decode()
parsers["FILN"] = parse_string

def parse_dirn(name, node, data):
    #todo: figure out what the rest of the guff is
    node.text = data[0:data.index(0)].decode()
parsers["DIRN"] = parse_dirn

def parse_int32(name, node, data):
    node.text = str(unpack("<I", data)[0])
parsers["RADI"] = parse_int32
parsers["IDNB"] = parse_int32
parsers["IDTY"] = parse_int32
parsers["BRIT"] = parse_int32
parsers["SELE"] = parse_int32
parsers["SCAL"] = parse_int32
parsers["AMBI"] = parse_int32
parsers["IDFI"] = parse_int32
parsers["BITS"] = parse_int32
parsers["WATR"] = parse_int32

def parse_3int32(name, node, data):
    node.text = str(unpack("<3I", data))
parsers["ANGS"] = parse_3int32
parsers["POSI"] = parse_3int32
parsers["OFST"] = parse_3int32
parsers["CENT"] = parse_3int32

def parse_6int32(name, node, data):
    node.text = str(unpack("<6I", data))
parsers["BBOX"] = parse_6int32

#def parse_rawd(name, node, data):
#    node.text = str(iter_unpack("<%dI", data) ???
#parsers["RAWD"] = parse_rawd

def parse_lfil(name, node, data):
    names = [x for x in iter_unpack("260s", data)]
    for name in (name[0].decode().strip('\x00') for name in names):
        child = ET.Element("name")
        child.text = name
        node.append(child)

parsers["LFIL"] = parse_lfil

def readGroup(data):
    ret = []
    while len(data) > 8:
        name, length = unpack_from('<4sI', data, 0)
        name = name.decode()
        node = ET.Element(name, {"length": str(length)})

        childdata = data[8:8+length]
        parsers[name](name, node, childdata)

        if name in groups:
            children = readGroup(childdata)
            for child in children:
                node.append(child)

        ret.append(node)
        data = data[8+length:]
    return ret

node = readGroup(data)[0]
node = md.parseString(ET.tostring(node))
print(node.toprettyxml())
#print(unknown)
