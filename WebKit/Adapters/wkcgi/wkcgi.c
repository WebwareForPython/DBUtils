// wkcgi.c

#include <stdlib.h>
#include <stdio.h>
#include "wkcgi.h"

int log_message(char * msg) {
	// fprintf (stderr, msg);
	return 0;
}

int sendCgiRequest(int sock, DictHolder* alldicts) {
	int bs = 0;
	int length=0;
	int totalsent=0;
	int content_length=0;
	char *buffer;
	int buflen=8092;
	char *len_str;

	bs = send( sock, alldicts->int_dict->str, alldicts->int_dict->ptr - alldicts->int_dict->str, 0);
	bs = 0;

	length = alldicts->whole_dict->ptr - alldicts->whole_dict->str;
	while (totalsent < length) {
		bs = send( sock, alldicts->whole_dict->str + totalsent, buflen>(length-totalsent)?length-totalsent:buflen, 0);
		if( bs < 0 ) {
			log_message("send() returned error code");
			return -1;
		}
		totalsent = totalsent + bs;
	}

	log_message("whole_dict sent\n");

	len_str = getenv("CONTENT_LENGTH");
	if (len_str !=NULL) {
		int read=0;
		int sent=0;
		int read_this_time=0;
		int sent_this_time=0;
		int amount_to_read=0;
		int amount_to_send=0;
		content_length = atoi(getenv("CONTENT_LENGTH"));
		log_message("There is post data");
		buffer = (char*) calloc(8092, 1);
		while (read < content_length) {
			amount_to_read = content_length-read;
			if( amount_to_read > 8092 ) {
				amount_to_read = 8092;
			}
			read_this_time = fread(buffer, 1, amount_to_read, stdin);
			if( read_this_time <= 0 ) {
				if( ferror(stdin) ) {
					log_message("error during fread(stdin)");
					return -1;
				} else {
					log_message("premature end of input on stdin");
					return -1;
				}
			}
			read += read_this_time;
			amount_to_send = read_this_time;
			while( amount_to_send > 0 ) {
				sent_this_time = send(sock, buffer+(read_this_time-amount_to_send), amount_to_send, 0);
				if( sent_this_time<=0 ) {
					log_message("send() returned error code");
					return -1;
				}
				sent += sent_this_time;
				amount_to_send -= sent_this_time;
			}
		}
	}

	log_message("Sent Request to server");

	//Let the AppServer know we're done
	shutdown(sock, 1);

	return 0;
}


int processCgiResponse(sock) {
	char* buff;
	int buflen = 8092;
	int br;

	buff = calloc(buflen,1);
	do {
		br = recv(sock, buff, buflen, 0);
		fwrite(buff, br, 1, stdout);
	} while (br > 0);

	return 1;
}


#ifdef WIN32
int winStartup() {
	WORD wVersionRequested;
	WSADATA wsaData;
	int err;

	_setmode(_fileno(stdin), _O_BINARY);
	_setmode(_fileno(stdout), _O_BINARY);
	wVersionRequested = MAKEWORD( 1, 0 );

	err = WSAStartup( wVersionRequested, &wsaData );
	if ( err != 0 ) {
	/* Tell the user that we could not find a usable */
	/* WinSock DLL.                                  */
		return 0;
	}
	return 1;
}
#endif

int main(char* argc, char* argv[]) {

	int sock = 0;
	DictHolder* dicts;
	char msgbuf[500];
	// char* addrstr = /*"localhost";//*/ "127.0.0.1";
	// int port = 8086;
	unsigned long addr;
	EnvItem **envItems;
	// int retryattempts = 10;
	// int retrydelay = 1;
	int retrycount = 0;
	Configuration* config;
#ifdef WIN32
	char configFile[500];
	char* p;
#endif

#ifdef WIN32
	winStartup();
#endif

	config = malloc(sizeof(Configuration));

#ifdef WIN32
	/* IIS runs CGI's in a different directory than they live in.  So */
	/* we need to construct the full path to the config file by */
	/* doing some string manipulation. */
	strcpy(configFile, argv[0]);
	p = strrchr(configFile, '\\');
	if( !p ) {
		p = strrchr(configFile, '/');
	}
	if( p ) {
		strcpy(p+1, ConfigFilename);
	} else {
		strcpy(configFile, ConfigFilename);
	}
	GetConfiguration(config, configFile);
#else
	GetConfiguration(config, ConfigFilename);
#endif

	// retryattempts = config->retry_attempts;
	// retrydelay = config->retry_delay;
	// addrstr = config->host;
	// port = config->port;

	addr = resolve_host(config->host);  //(addrstr);
	log_message("Got addr translation");

/*	while (sock < 0) {
		sock = wksock_open(addr, config->port);
	}
	*/

	while (sock <= 0 ) {
		sock = wksock_open(addr, config->port);
		if (sock > 0 || (retrycount > config->retry_attempts)) break;
		// if (errno != EAGAIN) break;
		sprintf(msgbuf, "Couldn't connect to AppServer,attempt %i of %i", retrycount, config->retry_attempts);
		log_message(msgbuf);
		retrycount++;
#ifdef WIN32
		Sleep(config->retry_delay*1000);
#else
		sleep(config->retry_delay);
#endif
	}

	if( sock <= 0 ) {
		return 1;
	}

	envItems = extractEnviron();
	dicts = createDicts(envItems);

	freeEnviron(envItems);

	log_message("created dicts");


	sendCgiRequest(sock, dicts);
	log_message("Sent Request\n");

	freeWFILE(dicts->int_dict);
	freeWFILE(dicts->whole_dict);
	free(dicts);

	processCgiResponse(sock);

	return 0;
}
