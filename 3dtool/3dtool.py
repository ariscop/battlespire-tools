#!/usr/bin/env python3
import sys
from collections import namedtuple
from struct import unpack, unpack_from, iter_unpack
from pprint import pprint

b3Dfile = namedtuple("b3dfile","""
    version
    pointCount
    planeCount
    radius
    unknown1
    unknown2
    planeDataOffset
    objectListOffset
    objectCount
    unknown3
    unknown4
    unknown5
    pointListOffset
    normalListOffset
    unknown6
    planeListOffset
""")

Point = namedtuple("Point", "x y z")
Plane = namedtuple("Plane", "unknown1 texture unknown2 points normal data")
PlanePoint = namedtuple("PlanePoint", "id u v")

def dataSlice(data, offset, length):
    return data[offset:offset+length]

def readPoints(hdr, data):
    for point in iter_unpack("<3i", dataSlice(data, hdr.pointListOffset, hdr.pointCount * 12)):
        yield Point(*point)

def readPlanes(hdr, data):
    planedata = [x[0] for x in iter_unpack("24s", dataSlice(data, hdr.planeListOffset, hdr.planeCount * 24))]
    normals   = [x[0] for x in iter_unpack("24s", dataSlice(data, hdr.planeListOffset, hdr.planeCount * 24))]
    offset = hdr.planeListOffset
    for i in range(0, hdr.planeCount):
        planePointCount, unknown1, texture, unknown2 = unpack_from("<2BH6s", data, offset)
        offset += 10
        planePoints = [PlanePoint(1+int((x[0])/12), *x[1:])
            for x in iter_unpack("<IHH", dataSlice(data, offset, planePointCount * 8))
        ]
        offset += planePointCount * 8

        yield Plane(unknown1, texture, unknown2, planePoints, normals[i], planedata[i])


#http://www.uesp.net/wiki/Daggerfall:ARCH3D.BSA + minor modifications?
#Notably the plane header is 10 bytes, not 8
#And textures are applied by level files, not
#by any property of the model
class b3DFile():
    def __init__(self, data):
        self.hdr = b3Dfile(*unpack_from("<4s15I", data, 0))
        self.data = data

    def points(self):
        return readPoints(self.hdr, self.data)
    def planes(self):
        return readPlanes(self.hdr, self.data)


def printObj(obj):
    for point in obj.points():
        print("v", *[x/16384 for x in point])
    for plane in obj.planes():
        print("f", *[x.id for x in plane.points])


data = b''
with open(sys.argv[1], "rb") as fd:
    data = fd.read()

printObj(b3DFile(data))
