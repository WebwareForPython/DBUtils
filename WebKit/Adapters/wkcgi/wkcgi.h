// wkcgi.h

#include "../common/wkcommon.h"
#include "../common/marshal.h"

int log_message(char* msg);
unsigned long resolve_host(char *value);
int wksock_open(unsigned long address, int port);
// DictHolder createDicts(EnvItem ** envItems);
