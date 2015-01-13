#!/usr/bin/env python3
import sys
from io import BytesIO
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

def readPoints(hdr, data):
    for point in iter_unpack("<3i", data[hdr.pointListOffset:][:hdr.pointCount * 12]):
        yield Point(*point)

def readPlanes(hdr, data):
    planedata = (x[0] for x in iter_unpack("24s", data[hdr.planeDataOffset:][:hdr.planeCount * 24]))
    normals   = (Point(*x) for x in iter_unpack("<3i", data[hdr.normalListOffset:][:hdr.planeCount * 24]))
    data = BytesIO(data[hdr.planeListOffset:])
    for plane, normal in zip(planedata, normals):
        planePointCount, unknown1, texture, unknown2 = unpack("<2BH6s", data.read(10))
        planePoints = [PlanePoint(int(point[0]/12), *point[1:])
            for point in iter_unpack("<IHH", data.read(planePointCount * 8))]
        yield Plane(unknown1, texture, unknown2, planePoints, normal, plane)


#http://www.uesp.net/wiki/Daggerfall:ARCH3D.BSA + minor modifications?
#Notably the plane header is 10 bytes, not 8
#And textures are applied by level files, not
#by any property of the model
class b3DFile():
    def __init__(self, data):
        self.hdr = b3Dfile(*unpack_from("<4s15I", data, 0))
        self.data = data
        self.points = [point for point in readPoints(self.hdr, self.data)]
        self.planes = [plane for plane in readPlanes(self.hdr, self.data)]

def printPly(obj):
    print("""ply
format ascii 1.0
element vertex %d
property int x
property int y
property int z
element face %d
property list uchar int vertex_index
end_header""" % (len(obj.points), len(obj.planes)))

    for point in obj.points:
        print("%d %d %d" % point)
    for plane in obj.planes:
        print("%d %s" % (len(plane.points), " ".join([str(x.id) for x in plane.points])))

def printObj(obj):
    for point in obj.points:
        print("v", *[x for x in point])
    for plane in obj.planes:
        print("f", *[x.id+1 for x in plane.points])

if __name__ == '__main__':
    with open(sys.argv[1], "rb") as fd:
        data = memoryview(fd.read())
    b3d = b3DFile(data)
    printPly(b3d)
