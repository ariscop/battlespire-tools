/**
 * bsafuse - Fuse driver for Battlespire-compatible BSA Files
 *
 * Written in 2011 by Andrew Cook ariscop@gmail.com
 *
 * To the extent possible under law, the author(s) have dedicated all
 * copyright and related and neighboring rights to this software to
 * the public domain worldwide. This software is distributed without
 * any warranty.
 *
 * You should have received a copy of the CC0 Public Domain
 * Dedication along with this software. If not,
 * see <http://creativecommons.org/publicdomain/zero/1.0/>.
 **/
#define FUSE_USE_VERSION 26

/**
 * This was written as a way to teach myself
 * about fuse and filesystems in general.
 * Not that useful but maybe it can help
 * someone else learn?
 **/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <endian.h>
#include <dirent.h>
#include <fuse.h>
#include <unistd.h>

#define u8 u_int8_t
#define u16 u_int16_t
#define u32 u_int32_t
#define s8 s_int8_t
#define s16 s_int16_t
#define s32 s_int32_t

//include <sys/xattr.h>

typedef enum bsa_type_t {
	NUM_RECORD = 0x0200,
	NAME_RECORD = 0x0100
}bsa_type;

typedef struct bsa_record_t {
	char name[14];
	u32 size;
	u32 offset;
	u32 RecordId;
} bsa_record;

typedef struct bsa_file_t {
	FILE *fd;
	u16 RecordCount;
	bsa_type type;
	bsa_record *Records;
} bsa_file;

#define PRIV_DATA ((bsa_file *) fuse_get_context()->private_data)

//TODO! Cleanup the cleanup functions
bsa_file *bsa_open_archive(char *path) {
	u32 count;
	u16 type;
	int i;
	bsa_file *bsa;

	bsa = malloc(sizeof(bsa_file));
	if(!bsa) return NULL;

	bsa->fd = fopen(path, "r");
	if(bsa->fd == NULL) { free(bsa); return NULL; }

	rewind(bsa->fd);
	if(!fread(&bsa->RecordCount, 2, 1, bsa->fd)) return NULL;
	if(!fread(&type, 2, 1, bsa->fd)) return NULL;

	type = le16toh(type);
	bsa->type = type;
	bsa->RecordCount = le32toh(bsa->RecordCount); //file in le, change to host

	if(type != NAME_RECORD && type != NUM_RECORD) return NULL;
		//!= || != insted of noexistent xor, unreliable on quantum computers

	bsa->Records = malloc(bsa->RecordCount * sizeof(bsa_record));
	if(!bsa->Records) return NULL;

	if(type == NAME_RECORD) {
		i = fseek(bsa->fd, (bsa->RecordCount * 18) * -1, SEEK_END);	//why a footer, why not a header?
	} else {														//seek to footer
		i = fseek(bsa->fd, (bsa->RecordCount * 8) * -1, SEEK_END);
	}

	if(i < 0) {free(bsa->Records); free(bsa); return NULL;};

	count = 4;
	if(type == NAME_RECORD) {
		for(i = 0; i < bsa->RecordCount; i++) {
			if(!fread(bsa->Records[i].name, 14, 1, bsa->fd)) { free(bsa->Records); free(bsa); return NULL; }
			if(!fread(&bsa->Records[i].size, 4, 1, bsa->fd)) { free(bsa->Records); free(bsa); return NULL; }
			bsa->Records[i].size = le32toh(bsa->Records[i].size);
			bsa->Records[i].RecordId = 0;
			bsa->Records[i].offset = count;
			count += bsa->Records[i].size;
		}
	} else {
		u_int32_t temp;
		for(i = 0; i < bsa->RecordCount; i++) {
			if(!fread(&temp, 4, 1, bsa->fd)) { free(bsa->Records); free(bsa); return NULL; }
			if(!fread(&bsa->Records[i].size, 4, 1, bsa->fd)) { free(bsa->Records); free(bsa); return NULL; }
			temp = le32toh(temp);
			bsa->Records[i].size = le32toh(bsa->Records[i].size);
			bsa->Records[i].RecordId = temp;
			bsa->Records[i].offset = count;
			sprintf(bsa->Records[i].name, "%d", temp);
			count += bsa->Records[i].size;
		}
	}
	return bsa;
}

int bsa_get_index(const char *path, bsa_file *file) {
	int i;
	const char *fpath = path;

	//skip leading /'s
	for(i = 0; i < 2; i++) {
		if(fpath[i] == 0x00) break;
		if(fpath[i] != '/') break;
		fpath++;
	}

	int min, max, p, ret;

	max = file->RecordCount - 1;
	min = 0;

	while(max >= min) {
		p = min + ((max - min) / 2);
		ret = strncmp(file->Records[p].name, fpath, 14);
		if(ret < 0) min = p + 1; //to prevent values from never converging
		if(ret > 0) max = p - 1; //and ignore the single check value at either end
		if(ret == 0) return p; //binary sorts are anoying
	}

/*	printf("min = %d, max = %d, p = %d, ret = %d, path = %s, name = %s\n", min, max, p, ret, fpath, file->Records[p].name);

	for(i = 0; i < file->RecordCount; i++) {
		if(strncmp(fpath, file->Records[i].name, 14) == 0) {
			printf("ERROR: Unsorted List: \"%s\" found at %d\n", fpath, i);
			return i;
		}
	}
*/
	//not found
	return -1;
};

int bsa_access(const char *path, int mode) {
	bsa_file *file = PRIV_DATA;

	if(strcmp("/", path) != 0) {
		int fh = bsa_get_index(path, file);
		if(fh < 0) return -2;
	}                          //exactly how this function is
                               //suposed to work is unclear,
                               //this appears to work though
	return 0;
};

int bsa_getattr(const char *path, struct stat *stats) {
	bsa_file *file = PRIV_DATA;

	memset(stats, 0, sizeof(struct stat));

	if(strcmp("/", path) == 0) {
		stats->st_mode = S_IFDIR | 0555;
		stats->st_size = 0;
		return 0;
	} else {
		int fh = bsa_get_index(path, file);
		if(fh < 0) return -2;
		stats->st_mode = S_IFREG | 0555;
		stats->st_size = file->Records[fh].size;
	}

	stats->st_nlink = 0;
	stats->st_atime = 0;
	stats->st_mtime = 0;
	stats->st_ctime = 0;
	return 0;
};

int bsa_open(const char *path, struct fuse_file_info *fi) {
	int fd;

	fd = bsa_get_index(path, PRIV_DATA);
	if (fd < 0) return -1;

	fi->fh = fd;
	return 0;
};

int bsa_read(const char *path, char *buf, size_t size, off_t offset, struct fuse_file_info *fi) {
	bsa_file *file = PRIV_DATA;
	if(fi->fh >= file->RecordCount) return -2; //invalid handle

	size_t filesize = file->Records[fi->fh].size;

	if(offset > filesize) return -1; //to big

	fseek(file->fd, file->Records[fi->fh].offset + offset, SEEK_SET);
	return fread(buf, 1, size, file->fd); //lazy byte count ftw!!!
};

int bsa_opendir(const char *path, struct fuse_file_info *fi) {
	if(strcmp(path, "/") != 0) return -1; //dont know if this can happen
	fi->fh = 1; //only root dir
	return 0;
}

int bsa_readdir(const char *path, void *buf, fuse_fill_dir_t filler, off_t offset, struct fuse_file_info *fi) {
	int i;
	bsa_file *file = PRIV_DATA;
	for(i = 0; i < file->RecordCount; i++)
		filler(buf, file->Records[i].name, NULL, 0);
	return 0;
};

//int bsa_init(struct fuse_conn_info *conn) {
//	//file = bsa_
//};

void bsa_destroy(void *ptr) {
	bsa_file *file = (bsa_file*)ptr;
	fclose(file->fd);
	free(file->Records);
	free(file);
};

static struct fuse_operations bsa_ops = {
	.readdir  = bsa_readdir,
	.open     = bsa_open,
	.read     = bsa_read,
	.access   = bsa_access,
	.getattr  = bsa_getattr,
//	.init     = bsa_init,
	.destroy  = bsa_destroy
};

int bsa_cleanup(bsa_file *bsa) {
	fclose(bsa->fd);
	free(bsa->Records);
	free(bsa);
	return 0;
}

int bsa_namecmp(const void *one, const void *two) {
	bsa_record *r1 = (bsa_record *)one;
	bsa_record *r2 = (bsa_record *)two;

	return strncmp(r1->name, r2->name, 14);

}

int main(int argc, char *argv[]) {
	bsa_file *file = NULL;

	file = bsa_open_archive(argv[1]);
	if(!file) {
		 printf("Error Opening File\n");
		 return -1;
	}

	qsort(file->Records, file->RecordCount, sizeof(bsa_record), bsa_namecmp);

	argv[1] = argv[2];
	argc--;

	return fuse_main(argc, argv, &bsa_ops, file);
}


//TODO! impliment error codes
//TODO! polish everything
