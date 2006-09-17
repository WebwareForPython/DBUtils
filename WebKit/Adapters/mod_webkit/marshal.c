/**************************************************************
 * marshal.c                                                  *
 * Handles the creation of Python marshal structures          *
 * Adapted from marshal.c in the Python distribution          *
 * Author: Jay Love (jsliv@jslove.org)                        *
**************************************************************/

#include <string.h>
#include "mod_webkit.h"


static char* expand_memory(WFILE* p, long add)
{
    char* newptr;
    long currsize;
    long newsize = 0;

    //log_message("Expanding Memory",p->r);

    currsize = p->end - p->str;
    if (add == 0) add = 4096;

    newsize = currsize + add;

    //sprintf(log_msg,"Expanding Memory from %i to %i", currsize, newsize);
    //log_message(log_msg, p->r);
    newptr = ap_pcalloc(p->r->pool, newsize);
    //if (!newptr) -- need a check here

    memcpy(newptr, p->str, currsize);
    p->end = newptr + newsize;
    p->ptr = newptr + (p->ptr - p->str);
    p->str = newptr;

    //log_message("Memory Expanded", p->r);
    return newptr;
}

void insert_data(WFILE* dest, WFILE* src)
{
    long src_len, dest_avail, len_need;

    //log_message("inserting data", dest->r);

    src_len = src->ptr - src->str;
    dest_avail = dest->end - dest->ptr;
    len_need = src_len - dest_avail;
    if (len_need > 0) { /* potential off by one here */
        expand_memory(dest, len_need+2);
    }
    memcpy(dest->ptr, src->str, src_len);
    dest->ptr = dest->ptr + src_len;
    //log_message("done inserting data", dest->r);

}

void w_more(int c, WFILE *p)
{
    //log_message("In w_more", p->r);
    if (p->str == NULL)
        return; /* An error already occurred, we're screwed */
    expand_memory(p, 0);
    *p->ptr++ = (char)c;
}

void w_string(const char *s, int n, WFILE *p)
{
    //log_message("In w_string", p->r);
    while (--n >= 0) {
        w_byte(*s, p);
        s++;
    }
}

void w_short(int x, WFILE *p)
{
    w_byte((char)( x      & 0xff), p);
    w_byte((char)((x>> 8) & 0xff), p);
}

void w_long(long x, WFILE *p)
{
    w_byte((char)( x      & 0xff), p);
    w_byte((char)((x>> 8) & 0xff), p);
    w_byte((char)((x>>16) & 0xff), p);
    w_byte((char)((x>>24) & 0xff), p);
}

#if SIZEOF_LONG > 4
void w_long64(long x, WFILE *p)
{
    w_long(x, p);
    w_long(x>>32, p);
}
#endif

void write_string(const char* s, WFILE* p)
{
    int len = (int)strlen(s);
    w_byte(TYPE_STRING, p);
    w_long((long)len, p);
    w_string(s, len, p);
    //log_message(s,p->r);
}

void write_integer(int number, WFILE* wf)
{
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
