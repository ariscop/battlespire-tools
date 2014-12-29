#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <endian.h>

typedef struct colour {
	unsigned char r, g, b;
} colour;

int main(int argc, char *argv[]) {
	char *file = argv[1];
	unsigned char section[7];
	unsigned char *buf, tmp;
	u_int16_t length, frames;
	int16_t width, height;
	long next;
	int i, x;

	colour cmap[256];
	colour pal[256];

	section[6] = 0x0;
	FILE *fd = fopen(file, "r");

/*	FILE *palfd = fopen("PAL.RAW", "r");
	if(palfd != NULL) {
		for(i = 0; i < 256; i++) {
			fread(&pal[i].r, 1, 1, fd);
			fread(&pal[i].g, 1, 1, fd);
			fread(&pal[i].b, 1, 1, fd);
			pal[i].r <<= 2;
			pal[i].g <<= 2;
			pal[i].b <<= 2;
		}
		fclose(palfd);
	} */

	while(1) {
		fread(section, 6, 1, fd);
		fprintf(stderr, "%s : ", section);
		if(fread(&length, 2, 1, fd) < 1) break;
		length = be16toh(length);
		if(strncmp(section, "BSIF", 4) == 0) length -= 8;
			//BUG! length in all other sections is from end of header
			//bsif sections are from start, fix
			//BUG BUG! bsif bsif is implicit on most files,
			//bsif files might be embeded in other files
			//INFO: yes, there are a few images in game.exe
			//INFO2: no, apparently, shows up 4 times, all of
			//them look like text sections or compressed
			//investigate later
			//INFO3 only ocours in BSI.BSA/SKEL00W0.BSI ?
			//INFO4 filename doesn't ocour anywhere else
			//maby a leftover beta file?
        fprintf(stderr, "%d\n", length);
		if(strncmp(section, "BSIF", 4) == 0) length = 0;
		next = ftell(fd) + length;

		if(strncmp(section, "CMAP", 4) == 0) {
			fprintf(stderr, "reading palett\n");
			for(i = 0; i < 256; i++) {
				fread(&cmap[i].r, 1, 1, fd);
				fread(&cmap[i].g, 1, 1, fd);
				fread(&cmap[i].b, 1, 1, fd);
				cmap[i].r <<= 2;
				cmap[i].g <<= 2;
				cmap[i].b <<= 2;
			}
		} else if(strncmp(section, "BSIF", 4) == 0) {
			fprintf(stderr, "reading bsif\n");
		} else if(strncmp(section, "BHDR", 4) == 0) {
			unsigned char bytes[4];
			fread(bytes, 4, 1, fd);
			fprintf(stderr, "\tBytes 0-3: %02X%02X%02X%02X\n", bytes[0], bytes[1], bytes[2], bytes[3]);
			fread(&width, 2, 1, fd);
			fprintf(stderr, "\tWidth %d\n", width);
			fread(&height, 2, 1, fd);
			fprintf(stderr, "\tHeight %d\n", height);
			fread(bytes, 4, 1, fd);
			fprintf(stderr, "\tBytes 8-11: %02X%02X%02X%02X\n", bytes[0], bytes[1], bytes[2], bytes[3]);
			fread(bytes, 2, 1, fd);
			fprintf(stderr, "\tBytes 12-13: %02X%02X\n", bytes[0], bytes[1]);
			fread(&frames, 2, 1, fd);
			fprintf(stderr, "\tFrames %d\n", frames);
			fread(bytes, 4, 1, fd);
			fprintf(stderr, "\tBytes 16-19: %02X%02X%02X%02X\n", bytes[0], bytes[1], bytes[2], bytes[3]);
			fread(bytes, 4, 1, fd);
			fprintf(stderr, "\tBytes 20-23: %02X%02X%02X%02X\n", bytes[0], bytes[1], bytes[2], bytes[3]);
			fread(bytes, 2, 1, fd);
			fprintf(stderr, "\tBytes 24-25: %02X%02X\n", bytes[0], bytes[1]);
			if(bytes[0] != 0) fprintf(stderr, "\tCompressed\n");
/*		} else if(strncmp(section, "DATA", 4) == 0) {
			fprintf(stderr, "writing image\n");
			u_int16_t header[2];
			u_int16_t tmp16;
			long pos, pos2;
			pos2 = ftell(fd);
			pos2 += length;
			for(i = 0; i < 0x100; i++) {
				fread(header, 4, 1, fd);
				pos = ftell(fd);
				fseek(fd, header[0], SEEK_CUR);
				fread(&tmp16, 2, 1, fd);
				for(x = 0; x < 0x40; x++) {
					fread(&tmp, 1, 1, fd);
					fwrite(&cmap[tmp].r, 1, 1, stdout);
					fwrite(&cmap[tmp].g, 1, 1, stdout);
					fwrite(&cmap[tmp].b, 1, 1, stdout);
				}
				fseek(fd, pos, SEEK_SET);
			}
			fseek(fd, pos2, SEEK_SET);*/
		} else	if(strncmp(section, "DATA", 4) == 0) {
			if((frames * (width * height)) != length) {
				int16_t offset;
				u_int16_t comp;
				unsigned char byte;
				long pos, start;
				int count, y;
				buf = malloc(width);
				start = ftell(fd);
				fprintf(stderr, "compressed\n");
				for(i = 0; i < (height * frames); i++) {
					fread(&offset, 2, 1, fd);
					fread(&comp, 2, 1, fd);
					pos = ftell(fd);
					fseek(fd, start + offset, SEEK_SET);
					if(comp == 0x0000) {
						fread(buf, width, 1, fd);
						for(x = 0; x < width; x++) {
							fwrite(&cmap[buf[x]].r, 1, 1, stdout);
							fwrite(&cmap[buf[x]].g, 1, 1, stdout);
							fwrite(&cmap[buf[x]].b, 1, 1, stdout);
						}
					} else {
						x = 0;
						while(x < width) {
							fread(&byte, 1, 1, fd);
							if(byte & 0x80) {
								byte &= 0x7f;
								count = byte;
								fread(&byte, 1, 1, fd);
								for(y = 0; y < count; y++) {
									fwrite(&cmap[byte].r, 1, 1, stdout);
									fwrite(&cmap[byte].g, 1, 1, stdout);
									fwrite(&cmap[byte].b, 1, 1, stdout);
									x++;
									if(x >= width) break;
								}
							} else {
								count = byte;
								for(y = 0; y < count; y++) {
									fread(&byte, 1, 1, fd);
									fwrite(&cmap[byte].r, 1, 1, stdout);
									fwrite(&cmap[byte].g, 1, 1, stdout);
									fwrite(&cmap[byte].b, 1, 1, stdout);
									x++;
									if(x >= width) break;
								}
							}
						}
					}
					fseek(fd, pos, SEEK_SET);
				}
			} else {
				fprintf(stderr, "writing image\n");
				for(i = 0; i < length; i++) {
					fread(&tmp, 1, 1, fd);
					fwrite(&cmap[tmp].r, 1, 1, stdout);
					fwrite(&cmap[tmp].g, 1, 1, stdout);
					fwrite(&cmap[tmp].b, 1, 1, stdout);
				}
			}
		} else {
			//
		}
		fseek(fd, next, SEEK_SET);

		if(strncmp(section, "END", 3) == 0) break;
	}
}
