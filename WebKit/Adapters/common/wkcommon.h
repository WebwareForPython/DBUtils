/* wkcommon.h */

#include <stdlib.h>
#include <ctype.h>
#include <sys/types.h>
#include <sys/stat.h>

#ifdef WIN32
#include <winsock.h>
#include <io.h>
#include <fcntl.h>
#include <time.h>
#define EINTR WSAEINTR
#define EAGAIN WSAEMFILE   //is this right????
#define strcasecmp _stricmp
#else
#include <sys/socket.h>
#include <netdb.h>
#include <errno.h>
#include <netinet/in.h>
#if defined(__MACH__) && defined(__APPLE__)
#include <nameser.h>
#endif
#include <resolv.h>
#endif

#include "marshal.h"
#include "environ.h"

#define ConfigFilename "webkit.cfg"

typedef struct {
	WFILE* int_dict;
	WFILE* whole_dict;
} DictHolder;

typedef struct {
	char* host;
	int port;
	int retry_attempts;
	int retry_delay;
} Configuration;

int log_message(char* msg);
DictHolder* createDicts(EnvItem ** envItems);
int wksock_open(unsigned long address, int port);
unsigned long resolve_host(char *value);
struct WFILE*  setup_WFILE();
int freeWFILE(struct WFILE* wf);
Configuration* GetConfiguration(Configuration*, char*);
