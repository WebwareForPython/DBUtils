/* marshal.c */
/* Author: Jay Love (jsliv@jslove.org) */
/* Adapted from marshal.c in the python distribution */
/* This file handles the creation of python marshal structures. */

#include <string.h>
#include <stdlib.h>
#include "marshal.h"

/*
#define w_byte(c, p) if ((p)->ptr != (p)->end) *(p)->ptr++ = (c); \
	else w_more(c, p)
*/

char* expand_memory(WFILE* p, long add) {
		char* newptr;
		long currsize;
		long newsize = 0;

		currsize = p->end - p->str;
		if (add == 0) add = 4096;

		newsize = currsize + add;

		newptr = calloc(newsize, 1);
		// if !newptr  //need a check here

		memcpy( newptr, p->str, currsize);
		p->end = newptr + newsize;
		p->ptr = newptr + (p->ptr - p->str);
		free(p->str);
		p->str = newptr;
		return newptr;
}

void insert_data(WFILE* dest, WFILE* src) {
		long src_len, dest_avail, len_need;

		src_len = src->ptr - src->str;
		dest_avail = dest->end - dest->ptr;
		len_need = src_len - dest_avail;
		if (len_need > 0) { // potential off by one here
				expand_memory(dest, len_need+1);
		}
		memcpy(dest->ptr, src->str, src_len);
		dest->ptr += src_len;
}

void w_more(char c, WFILE* p) {
	if (p->str == NULL)
		return; /* An error already occurred, we're screwed */
	expand_memory(p, 0);
	*p->ptr++ = c;
}

void w_byte(char c, WFILE* p) {
	if ((p)->ptr != (p)->end)
		*(p)->ptr++ = (c);
	else w_more(c, p);
}

void w_string(char* s, int n, WFILE* p) {
		// log_message("In w_string", p->r);
		while (--n >= 0) {
			w_byte(*s, p);
			s++;
		}
}

void w_short(int x, WFILE* p) {
	w_byte( x      & 0xff, p);
	w_byte((x>> 8) & 0xff, p);
}

void w_long(long x, WFILE* p) {
	w_byte((int)( x      & 0xff), p);
	w_byte((int)((x>> 8) & 0xff), p);
	w_byte((int)((x>>16) & 0xff), p);
	w_byte((int)((x>>24) & 0xff), p);
}

#if SIZEOF_LONG > 4
void w_long64(long x, WFILE *p)
{
	w_long(x, p);
	w_long(x>>32, p);
}
#endif

void write_string( char* s, long len, WFILE* p) {
	w_byte(TYPE_STRING, p);
	w_long(len, p);
	if (len > 0)
			w_string( s, len, p);
}

void write_integer(int number, WFILE* wf) {
	long x;
	x = (long)number;
#if SIZEOF_LONG > 4
	long y = x>>31;
	if (y && y != -1) {
		w_byte(TYPE_INT64, wf);
		w_long64(x, wf);
	}
	else
#endif
		{
		w_byte(TYPE_INT, wf);
		w_long(x, wf);
	}
}
