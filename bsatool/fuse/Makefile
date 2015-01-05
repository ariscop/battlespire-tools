CC=gcc

bsafuse : bsafuse.o
	$(CC) -g `pkg-config fuse --libs` -o bsafuse bsafuse.o

bsafuse.o : bsafuse.c
	$(CC) -g -Wall `pkg-config fuse --cflags` -c bsafuse.c

clean:
	rm -f bsafuse *.o
