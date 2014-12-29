#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

//include <gl.h>
//include <sdl.h>

#include "types.h"

typedef struct Point {
	int32_t x, y, z;
} Point;

typedef struct PlanePoint {
	int Point;
	int32_t PointOffset;
	int16_t U, V;
} PlanePoint;

typedef struct Plane {
	u_int16_t Texture;
	int8_t PlanePointCount;
	PlanePoint *Points;
} Plane;

int b3d_parse(char *buf) {
	int i, x, y, offset;
	int first, prev;
	int32_t PointCount;
	int32_t PlaneCount;
	int32_t PointListOffset;
	int32_t PlaneListOffset;
	Point      *Points;
	PlanePoint *PlanePoints;
	Plane      *Planes;

	Planes = malloc(sizeof(Plane));

	memcpy(&PointCount, &buf[4], 4);
	memcpy(&PlaneCount, &buf[8], 4);

	memcpy(&PointListOffset, &buf[48], 4);
	memcpy(&PlaneListOffset, &buf[60], 4);

	offset = PointListOffset;
	Points = malloc(sizeof(Point) * PointCount);
	for(i = 0; i < PointCount; i++) {
		memcpy(&Points[i].x, &buf[offset], 4);
		memcpy(&Points[i].y, &buf[offset + 4], 4);
		memcpy(&Points[i].z, &buf[offset + 8], 4);
		offset += 12;
	}

	offset = PlaneListOffset;
	Planes = malloc(sizeof(Plane) * PlaneCount);
	for(i = 0; i < PlaneCount; i++) {
		memcpy(&Planes[i].PlanePointCount, &buf[offset], 1);
		//printf("%02x\n", Planes[i].PlanePointCount);
		memcpy(&Planes[i].Texture, &buf[offset + 2], 1);
		offset += 8 + 2;
		Planes[i].Points = malloc(sizeof(PlanePoint) * Planes[i].PlanePointCount);
		for(x = 0; x < Planes[i].PlanePointCount; x++) {
			memcpy(&Planes[i].Points[x].PointOffset, &buf[offset], 4);
			//printf("\t%08X\n", Planes[i].Points[x].PointOffset);
			memcpy(&Planes[i].Points[x].U, &buf[offset + 4], 2);
			memcpy(&Planes[i].Points[x].V, &buf[offset + 6], 2);
			Planes[i].Points[x].Point = Planes[i].Points[x].PointOffset / 12;
			prev = y;
			y = Planes[i].Points[x].Point;
			if(x == 0) first = y;
//			if(totri) {
			if(Planes[i].PlanePointCount > 3) {
				if(x < 3) {
					printf("%d\t%d\t%d\t", Points[y].x, Points[y].y, Points[y].z);
				} else {
					printf("\n%d\t%d\t%d\t", Points[first].x, Points[first].y, Points[first].z);
					printf("%d\t%d\t%d\t", Points[prev].x, Points[prev].y, Points[prev].z);
					printf("%d\t%d\t%d\t\n", Points[y].x, Points[y].y, Points[y].z);
				}
			} else {
				printf("%d\t%d\t%d\t", Points[y].x, Points[y].y, Points[y].z);
			}
			offset += 8;
		}
		if(Planes[i].PlanePointCount <= 4) printf("\n");
	}

}

int main(int argc, char *argv[]) {
	char *file = argv[1];
	char *buffer;
	int len;
	FILE *fd = fopen(file, "r");

	fseek(fd, 0, SEEK_END);
	len = ftell(fd);
	buffer = malloc(len);
	rewind(fd);

	fread(buffer, len, 1, fd);
	fclose(fd);

	b3d_parse(buffer);
	free(buffer);

}
