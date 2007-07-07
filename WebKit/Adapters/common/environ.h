/* Environ.h */

#ifndef ENVIRON_H
#define ENVIRON_H

typedef struct {
	char* key;
	char* val;
} EnvItem;

int log_message(char* msg);
EnvItem* splitEnviron(char* envstr);
EnvItem** extractEnviron();
int freeEnviron(EnvItem** env);

#endif

