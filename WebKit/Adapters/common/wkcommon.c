/*  Common Functions */

#include "wkcommon.h"

#include <string.h>
#include <stdio.h>
#include <sys/stat.h>
#include "parsecfg.h"

DictHolder* createDicts(EnvItem ** envItems) {
	char *key, *val;
	int i=0;
	int length=0;
	WFILE* int_dict = NULL;
	WFILE* env_dict= NULL;
	WFILE* whole_dict=NULL;
	DictHolder* dictholder;
	// char msg[500];

	dictholder = calloc(sizeof(DictHolder),1);

	dictholder->int_dict = NULL;
	dictholder->whole_dict = NULL;

	env_dict = setup_WFILE();
	whole_dict = setup_WFILE();
	int_dict = setup_WFILE();

	if (env_dict == NULL || whole_dict == NULL || int_dict == NULL) {
			log_message("Couldn't allocate Python data structures");
			return dictholder;
	}

	// log_message("extracted environ");

	// start dictionary
	w_byte(TYPE_DICT, env_dict);

	for (i = 0; envItems[i] != NULL; i++) {
			key = envItems[i]->key;
			val = envItems[i]->val;

			// sprintf(msg, "Adding dict key=%.100s, val=%.100s", key, val);
			// log_message(msg);

			write_string(key, (int) strlen(key), env_dict);
			if (val != NULL) write_string(val, strlen(val), env_dict);
			else w_byte(TYPE_NONE, env_dict);
	}
	w_byte(TYPE_NULL, env_dict);
	// end dictionary

	log_message("Built env dictionary");

	// We can start building the full dictionary now
	w_byte(TYPE_DICT, whole_dict);
	write_string("format", 6, whole_dict); //key
	write_string("CGI", 3, whole_dict);  //value
	write_string("time", 4, whole_dict); //key
	w_byte(TYPE_INT, whole_dict);  //value
	// This won't work.  Marshal converts this from a float to a string,
	// I have neither. Floats are ugly.
	w_long((long)time(0), whole_dict);//value

	write_string("environ", 7, whole_dict); //key

	// copy env_dict into whole_dict
	insert_data(whole_dict, env_dict);
	freeWFILE(env_dict); //free this dict as we don't need it any longer

	// that should be it
	// end dictionary
	w_byte(TYPE_NULL, whole_dict);

	// Setup the integer dict
	length = whole_dict->ptr - whole_dict->str;
	write_integer((int)length, int_dict);

	dictholder->int_dict = int_dict;
	dictholder->whole_dict = whole_dict;
	//now we send it

	return dictholder;
}

/* ========================================================================= */
/* Open a socket to appserver host */
/* Taken from apache jserv.
/*
/* ======================================================================== */
int wksock_open(unsigned long address, int port) {
	struct sockaddr_in addr;
	int sock;
	int ret;

	/* Check if we have a valid host address */
	if (address==0) {
		// log_message("cannot connect to unspecified host");
		return -1;
	}

	/* Check if we have a valid port number. */
	if (port < 1024) {
		// log_message("invalid port, must be geater than 1024");
		//port = 8007;
	}
	addr.sin_addr.s_addr = address;
	addr.sin_port = htons((unsigned short)port);
	addr.sin_family = AF_INET;

	/* Open the socket */
	sock = socket( AF_INET, SOCK_STREAM, 0);
	if (sock==-1) {
#ifndef WIN32
		return -1;
#else
		int err = WSAGetLastError();
		return -1;
#endif
    }

	/* Tries to connect to appserver (continues trying while error is EINTR) */
	do {
		ret=connect(sock,(struct sockaddr *)&addr,sizeof(struct sockaddr_in));
	#ifdef WIN32
		if (ret==SOCKET_ERROR) errno=WSAGetLastError()-WSABASEERR;
	#endif /* WIN32 */
	} while (ret==-1 && (errno==EINTR || errno == EAGAIN));

	/* Check if we connected */
	if (ret==-1) {
		// log_message("Can not connect to WebKit AppServer");
		return -1;
	}
	#ifdef TCP_NODELAY
	{
		int set = 1;
		setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, (char *)&set,
		sizeof(set));
	}
	#endif

	/* Return the socket number */
	return sock;
}

/* ========================================================================= */
/* Returns a unsigned long representing the ip address of a string */
/* ========================================================================= */
unsigned long resolve_host(char *value) {
	int x;

	/* Check if we only have digits in the string */
	for (x=0; value[x]!='\0'; x++)
		if (!isdigit(value[x]) && value[x] != '.') break;

	if (value[x] != '\0') {
		/* If we found also characters we use gethostbyname()*/
		struct hostent *host;

		host=gethostbyname(value);
		if (host==NULL) return 0;
		return ((struct in_addr *)host->h_addr_list[0])->s_addr;
	} else {
		/* If we found only digits we use inet_addr() */
		return inet_addr(value);
	}
	return 0;
}

/* ====================================================== */
/*  Initialize the WFILE structure
 *  This is used by the marshalling functions.
/* ======================================================= */
struct WFILE*  setup_WFILE() {
		struct WFILE* wf = NULL;
		wf = calloc(sizeof(WFILE),1);
		if (wf == NULL) {
			// log_message("Failed to get WFILE structure\n");
			return wf;
		}
		wf->str = NULL; wf->ptr = NULL; wf->end = NULL;
		wf->str = calloc(4096,1);

		if (wf->str == NULL) {
			// log_message("Couldn't allocate memory");
			return NULL;
		}
		wf->end = wf->str + 4096;
		wf->ptr = wf->str;
		return wf;
}


int freeWFILE(struct WFILE* wf) {
	free(wf->str);
	free(wf);
	return 1;
}

Configuration* GetConfiguration(Configuration* config, char* configFile) {
	// FILE* cfgfile;
	// struct stat statbuf;
	// int result;
	// int size;
	// char* host;
	// char* portstr;
	int mark=0;
	// int port;
	// char c;
	// Configuration* config;
	int rv;

	// config = malloc(sizeof(Configuration));

	cfgStruct cfg[]={	/* this must be initialized */
		/* parameter			type		address of variable */
		{"Host",				CFG_STRING,	&config->host					},
		{"Port",				CFG_INT,	(int*)&(config->port)			},
		{"MaxConnectAttempts",	CFG_INT,	(int*)&(config->retry_attempts)},
		{"ConnectRetryDelay",	CFG_INT,	(int*)&(config->retry_delay)	},
	};

	config->host = "localhost";
	config->port = 8086;
	config->retry_attempts = 10;
	config->retry_delay = 1;

	log_message("Trying to parse config file");

	rv = cfgParse(configFile, cfg, CFG_SIMPLE);

	log_message("Got config");

	if(rv == -1) {
		log_message("Whoops, Couldn't get config info");
	}

	// fprintf(stderr, "Host: %s\n",config->host);
	// fprintf(stderr, "Port: %i\n", config->port);

	// fprintf(stderr, "Attempts: %i\n",config->retry_attempts);
	// fprintf(stderr, "Delay: %i\n", config->retry_delay);

	return config;

	/*
	result = stat(configFile, &statbuf);
	size = statbuf.st_size;
	if (size > 500) return NULL;

	host = malloc(size+1);
	portstr = malloc(size+1);
	cfgfile = open(configFile, "r");

	c = fgetc(cfgfile);
	while (c != ":") {
		*(host+mark) = c;
		c = fgetc(cfgfile);
	}

	mark=0;
	c = fgetc(cfgfile);
	while (c != ":") {
		*(portstr+mark) = c;
		c = fgetc(cfgfile);
	}

	port = atoi(portstr);

	config->port = port;
	config->host=host;

	return NULL;

	*/
}
