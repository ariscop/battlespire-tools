from construct import *

CHUNKS = {}

CHUNKS["BHDR"] = Struct(
    Const(26, Int32ub),
    "xoffset"   / Int16sl,
    "yoffset"   / Int16sl,
    "width"     / Int16sl,
    "height"    / Int16sl,
    "u4"        / Int16sl,
    Const(0, Int32sl),
    "frames"    / Int16sl,
    "u6"        / Int16sl,
    "u7"        / Int16sl,
    "u8"        / Int8ul,
    "u9"        / Int8ul,
    "u10"       / Int8ul,
    "u11"       / Int8ul,
    "flags"     / Int16sl,
)

CHUNKS["IFHD"] = Struct(
    Const(44, Int32ub),
    "u1" / Int32sl,
    "u2" / Int32sl,
    Const(0, Int32sl)[9],
)

def _sized(n):
    return FocusedSeq("_dat", Const(n, Int32ub), "_dat" / Bytes(n))

CHUNKS["DATA"] = FocusedSeq("_dat", "_len" / Int32ub, "_dat" / Bytes(this._len))
CHUNKS["NAME"] = Prefixed(Int32ub, CString("ascii"))
CHUNKS["HICL"] = _sized(256)
CHUNKS["HTBL"] = _sized(8192)
CHUNKS["CMAP"] = _sized(768)
CHUNKS["END "] = Const(0, Int32ub)
CHUNKS["BSIF"] = Int32ub

BSIFile = GreedyRange(Struct(
    "tag" / PaddedString(4, "ascii"),
    "dat" / Switch(this.tag, CHUNKS, default=Error),
))

__all__ = ["BSI"]
