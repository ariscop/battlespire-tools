#!/usr/bin/env python3

import numpy as np

from io import BytesIO
from bsistructs import BSIFile
from PIL import Image
from PIL.ImagePalette import ImagePalette

int32ul = np.dtype("<u4")
int16ul = np.dtype("<u2")

class BSI:
    __slots__ = "IFHD", "NAME", "BHDR", "HICL", "HTBL", "CMAP", "DATA"

    def __init__(self, NAME=None, IFHD=None, BHDR=None):
        self.NAME = NAME
        self.IFHD = IFHD
        self.BHDR = BHDR
        self.HICL = None
        self.HTBL = None
        self.CMAP = None
        self.DATA = None

    def decomp(self):
        width, height, frames = self.BHDR.width, self.BHDR.height, self.BHDR.frames

        index = np.frombuffer(self.DATA, dtype=int32ul, count=(height * frames))

        inbuf = BytesIO(self.DATA)
        out = BytesIO()

        for idx in index:
            c = bool(idx & 0x80000000)
            idx &= 0x7FFFFFFF
            inbuf.seek(idx)
            if not c:
                out.write(inbuf.read(width))
            else:
                i = 0
                while i != width:
                    c, = inbuf.read(1)
                    rle = c & 0x80
                    c &= 0x7F
                    if rle:
                        pixel = inbuf.read(1)
                        for count in range(0, c):
                            out.write(pixel)
                    else:
                        out.write(inbuf.read(c))
                    i += c

        return out.getvalue()

    def hicl_to_pal(self):
        hicl = np.frombuffer(self.HICL, dtype=int16ul)
        out  = np.zeros([256, 3], dtype=np.uint8)
        for x in range(128):
            c = hicl[x]
            out[x << 1] = (
                ((c >> 11) & 0x1F) * 8, # r
                ((c >>  6) & 0x1F) * 8, # g
                ((c >>  1) & 0x1F) * 8, # b
            )
        out = out.transpose()
        pal = ImagePalette(palette=out.tobytes())
        return pal

    def dump_img(self, out):
        BHDR = self.BHDR
        b = self.DATA
        if BHDR.flags != 0:
            b = self.decomp()

        pal = self.hicl_to_pal()

        img = Image.frombytes('P', (BHDR.width, BHDR.height * BHDR.frames), b)
        img.putpalette(pal)
        img.save(out)

from pathlib import Path
from argparse import ArgumentParser, FileType

argparser = ArgumentParser()
argparser.add_argument("file", type=FileType("rb"))
argparser.add_argument("out", type=Path)

def main(argv=None):
    args = argparser.parse_args(argv)

    with args.file as fd:
        chunks = BSIFile.parse_stream(fd)

    imgs = []
    img = None
    name = None
    ifhd = None

    for chunk in chunks:
        tag, dat = chunk.tag, chunk.dat
        if tag in ("BSIF", "END "):
            pass
        elif tag == "IFHD":
            ifhd = dat
        elif tag == "NAME":
            name = dat
        elif tag == "BHDR":
            img = BSI(NAME=name, IFHD=ifhd, BHDR=dat)
        elif tag == "DATA":
            setattr(img, tag, dat)
            imgs.append(img)
            img = None
        else:
            setattr(img, tag, dat)

    if args.out:
        imgs[0].dump_img(args.out)

if __name__ == "__main__":
    main()
