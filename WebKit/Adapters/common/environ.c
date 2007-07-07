/* Test file for routines needed for webkit cgi executable */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "environ.h"

extern char** environ;

/*********************************************
* Extract environ item from a string into an EnvItem, used for cgi
**********************************************/
EnvItem* splitEnviron(char* envstr) {
	EnvItem* item;
	int fullLen;
	int index = 0;
	char delim = '=';

	fullLen = strlen(envstr);
	item = calloc(sizeof(EnvItem),1);

	while (index < fullLen) {
		if ( envstr[index] == delim) break;
		else index ++;
	}

	item->key = calloc(sizeof(char), index+1);
	item->val = calloc(sizeof(char), fullLen-index);

	memcpy(item->key, envstr, index);
	memcpy(item->val, envstr+index+1, fullLen - index);

	return item;
}

int environLength() {
	int count = 0;
	while (environ[count] != NULL) {
		count++;
	}
	return count;
}

EnvItem** extractEnviron() {
	int envItems;
	int item = 0;
	EnvItem **itemList;

	envItems = environLength();

	itemList = (EnvItem**) calloc(sizeof(EnvItem*), envItems+1);

	while (environ[item] != NULL) {
		itemList[item] =  splitEnviron(environ[item]);
		item++;
	}

	return itemList;
}

int freeEnviron( EnvItem** env) {
	int i;
	// char msg[400];

	// sprintf(msg, "Starting to free environment\r\n");
	// log_message(msg);

	for(i=0; env[i] != NULL; i++) {
		// sprintf(msg, "Freeing item %i", i);
		// log_message(msg);
		// sprintf(msg, "Freeing key %.100s", env[i]->key);
		// log_message(msg);
		if (env[i]->key !=NULL) free(env[i]->key);
		// sprintf(msg, "Freeing val %.100s", env[i]->val);
		// log_message(msg);
		if (env[i]->val !=NULL) free(env[i]->val);
		free(env[i]);
	}
	log_message("EnvItems freed");
	free(env);
	return 1;
}

#if 0

int main(char argc, char* argv[]) {

	EnvItem** list;
	int count = 0;

	list = extractEnviron();
	while (list[count] != NULL) {
		printf( "Key: %s Val: %s\n", list[count]->key, list[count]->val);
		count++;
		}
	freeEnviron(list);
	exit(0);

}

#endif
