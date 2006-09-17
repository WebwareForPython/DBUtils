/* Windows ISAPI Dll for WebKit */


#include <httpext.h>
#include <string.h>
#include <stdio.h>

#include "wk_isapi.h"

static const char isa_desc[]="WebKit ISAPI Extension Ver 0";

int DEBUG=0;
static LPEXTENSION_CONTROL_BLOCK staticecb;


static char* HEADERS[37]= {
"AUTH_PASSWORD",// Specifies the value entered in the client's authentication dialog. This variable is only available if Basic authentication is used.  
"AUTH_TYPE", // Specifies the type of authentication used. If the string is empty, then no authentication is used. Possible values are Kerberos, user, SSL/PCT, Basic, and integrated Windows authentication. 
"AUTH_USER", // Specifies the value entered in the client's authentication dialog box. 
"CERT_COOKIE", // Specifies a unique ID for a client certificate. Returned as a string. Can be used as a signature for the whole client certificate. 
"CERT_FLAGS", // If bit0 is set to 1, a client certificate is present. If bit1 is set to 1, the certification authority (CA) of the client certificate is invalid (that is, it is not on this server's list of recognized CAs). 
"CERT_ISSUER", // Specifies the issuer field of the client certificate. For example, the following codes might be O=MS, OU=IAS, CN=user name, C=USA, and so on. 
"CERT_KEYSIZE", // Specifies the number of bits in the Secure Sockets Layer (SSL) connection key size. 
"CERT_SECRETKEYSIZE", // Specifies the number of bits in the server certificate private key. 
"CERT_SERIALNUMBER", // Specifies the serial-number field of the client certificate. 
"CERT_SERVER_ISSUER", // Specifies the issuer field of the server certificate. 
"CERT_SERVER_SUBJECT", // Specifies the subject field of the server certificate. 
"CERT_SUBJECT", // Specifies the subject field of the client certificate. 
"CONTENT_LENGTH", // Specifies the number of bytes of data that the script or extension can expect to receive from the client. This total does not include headers. 
"CONTENT_TYPE", // Specifies the content type of the information supplied in the body of a POST request. 
"LOGON_USER", // The Windows account that the user is logged into. 
"HTTPS", // Returns on if the request came in through secure channel (with SSL encryption), or off if the request is for an unsecure channel.  
"HTTPS_KEYSIZE", // Specifies the number of bits in the SSL connection key size. 
"HTTPS_SECRETKEYSIZE", // Specifies the number of bits in server certificate private key. 
"HTTPS_SERVER_ISSUER", // Specifies the issuer field of the server certificate. 
"HTTPS_SERVER_SUBJECT", // Specifies the subject field of the server certificate. 
"INSTANCE_ID", // Specifies the ID for the server instance in textual format. If the instance ID is 1, it appears as a string. This value can be used to retrieve the ID of the Web-server instance, in the metabase, to which the request belongs. 
"INSTANCE_META_PATH", // Specifies the metabase path for the instance to which the request belongs.  
"PATH_INFO", // Specifies the additional path information, as given by the client. This consists of the trailing part of the URL after the script or ISAPI DLL name, but before the query string, if any. 
"PATH_TRANSLATED", // Specifies this is the value of PATH_INFO, but with any virtual path expanded into a directory specification. 
"QUERY_STRING", // Specifies the information that follows the first question mark in the URL that referenced this script. 
"REMOTE_ADDR", // Specifies the IP address of the client or agent of the client (for example gateway, proxy, or firewall) that sent the request. 
"REMOTE_HOST", // Specifies the host name of the client or agent of the client (for example, gateway, proxy or firewall) that sent the request if reverse DNS is enabled. Otherwise, this value is set to the IP address specified by REMOTE_ADDR. 
"REMOTE_USER", // Specifies the user name supplied by the client and authenticated by the server. This comes back as an empty string when the user is anonymous. 
"REQUEST_METHOD", // Specifies the HTTP request method verb. 
"SCRIPT_NAME", // Specifies the name of the script program being executed. 
"SERVER_NAME", // Specifies the server"s host name, or IP address, as it should appear in self-referencing URLs. 
"SERVER_PORT", // Specifies the TCP/IP port on which the request was received. 
"SERVER_PORT_SECURE", // Specifies a string of either 0 or 1. If the request is being handled on the secure port, then this will be 1. Otherwise, it will be 0. 
"SERVER_PROTOCOL", // Specifies the name and version of the information retrieval protocol relating to this request.  
"SERVER_SOFTWARE", // Specifies the name and version of the Web server under which the ISAPI extension DLL program is running. 
"URL", //Specifies the base portion of the URL. Parameter values will not be included. The value is determined when IIS parses the URL from the header. 
NULL, //end
};




int log_message(char* msg) {
	if(DEBUG) {
		int msglen = strlen(msg);
//		staticecb->WriteClient(staticecb->ConnID, msg, &msglen, HSE_IO_SYNC);	
		FILE* debugfile;
		debugfile = fopen("C:\\temp\\wkisapi_debug.txt","a+b");
		fwrite( msg, msglen, 1, debugfile);
		fwrite( "\r\n", strlen("\r\n"), 1, debugfile);
		fflush(debugfile);
		fclose(debugfile);
	}
	return 0;
}

/********************************************
*Send a request to the AppServer
*Pass in a socket and a DictHolder, and the ecb
*
*********************************************/
int sendISAPIRequest(int sock, DictHolder* alldicts, LPEXTENSION_CONTROL_BLOCK ecb) {

	int bs = 0; //bytes sent
	unsigned long length=0;  //length of data to send
	unsigned long totalsent=0;  //size of data sent
	int content_length=0;  //
	char *buff;  //buffer
	int buflen=8092;  //size of buff
	char msg[500];   //for debug messages




	//Send integer specifying the size of the request dictionary
	length = alldicts->int_dict->ptr - alldicts->int_dict->str;
	while (totalsent < length) {
		bs = send( sock, alldicts->int_dict->str, length - totalsent, 0);
		if (bs < 0) return 0;
		totalsent = bs+totalsent;
	}


	//send the request dictionary
	bs = 0;
	totalsent=0;
	length = alldicts->whole_dict->ptr - alldicts->whole_dict->str;
	
	while (totalsent < length) {	  
		bs = send( sock, alldicts->whole_dict->str + totalsent, buflen>(length-totalsent)?length-totalsent:buflen, 0);
		if (bs < 0) return 0;
		totalsent = totalsent + bs;
	}


	//Send any post data
	length = ecb->cbTotalBytes;
	if (length != 0) {
	  long read=0;
	  long sent=0;
	  log_message("There is post data");

	  //send data that IIS has already recieved from the client
	  while (sent < ecb->cbAvailable)
		sent = sent + send(sock, (char*)(ecb->lpbData + sent), ecb->cbAvailable - sent, 0);
	  if (sent < length) {
		int dwSize;
		int *lpdwSize;
		dwSize = buflen;

		sent = 0;
		buff = (char*) calloc(8092,1);

		while (sent < (length - ecb->cbAvailable)) {
			lpdwSize = &dwSize;
			if( ecb->ReadClient(ecb->ConnID, buff, lpdwSize)) 
				sent = sent + send(sock, buff, *lpdwSize, 0);
			else {
				free(buff);
				return 0;
			}
		}
		free(buff);
		sprintf(msg, "Freed extra post data buffer in sendISAPIRequest with sizeof %i", sizeof(buff));
		log_message(msg);

	  }
	}
  //Done sending post data

	log_message("Sent Request to server");

	//Let the AppServer know we're done
	shutdown(sock, 1);
	
	return 1;
};


/*******************
*Generate the environment variables needed by taking data from the ecb and IIS
*Pass in an ecb, returns a pointer to a NULL terminated array of EnvItem pointers
**************/
EnvItem** generateEnvItems(LPEXTENSION_CONTROL_BLOCK ecb) {

	int envItemCount, httpItemCount;
	int item = 0;
	EnvItem **itemList;
	char* buff;
	int itemlen = 128;  //default buffer size
	int* pitemlen;
	EnvItem* envitem;
	int skipped = 0;
	char* ptr;
	int keylength, valuelength, marker, i;
	char msg[400];
	int newline = '\n';
	int colon = ':';

	envItemCount = sizeof(HEADERS)/sizeof(char*);


	//How many http headers are there?
	httpItemCount=0;
	pitemlen = &itemlen;
	ptr = NULL;

	buff = calloc(itemlen, 1);
	if( ! ecb->GetServerVariable(ecb->ConnID, "ALL_HTTP", buff, pitemlen))
	{	//we didn't have a big enough buffer, but pitemlen now has the correct size
		free(buff); 
		buff = NULL;
		buff = calloc(*pitemlen,1);
		if( ! ecb->GetServerVariable(ecb->ConnID, "ALL_HTTP", buff, pitemlen)) {
			free(buff);
			return NULL;
		}
	}	
	ptr=buff;
	//count how many HTTP headers there are by looking for \n's
	while( (ptr = strchr(ptr, newline)) != NULL) {
		httpItemCount++;
		ptr = ptr+1; //skip the \n we just found
	}

	sprintf(msg,"Found %i HTTP headers",httpItemCount);
	log_message(msg);
	ptr = NULL;

	//now we know how many envItems we'll have, and can get the memory for the array
	itemList = (EnvItem**) calloc(sizeof(void*), envItemCount+httpItemCount);
	if (itemList == NULL) {
		free(buff);
		return NULL;
	}

	//Split up HTTP headers, buff already has them, and *pitemlen is the length of the buffer
	marker=0; keylength=0; valuelength=0;
	for(i=0; i<(httpItemCount); i++) {
		envitem      = (EnvItem*)calloc(sizeof(EnvItem), 1);
		keylength    = strchr(buff+marker, colon) - (buff+marker); //find the next colon
		valuelength  = strchr(buff+marker+keylength+1, newline) - (buff+marker+keylength+1); //find the newline after the colon
		envitem->key = calloc(sizeof(char) * keylength+1, 1);
		envitem->val = calloc(sizeof(char) * valuelength+1, 1);
		memcpy(envitem->key, buff+marker, keylength);
		memcpy(envitem->val, buff+marker+keylength+1, valuelength);
		itemList[i]=envitem;
		marker = marker + keylength + valuelength + 2;  //the plus 2 is for the : and \n
	}

	free(buff);
	sprintf(msg, "Freed htpheaders buffer in generateEnvItems with sizeof %i", sizeof(buff));
	log_message(msg);

//Done with http headers


	pitemlen = &itemlen;
	while (HEADERS[item] != NULL ) {
		buff = calloc(*pitemlen, 1);
		if (buff == NULL) return NULL; 
		if( ! ecb->GetServerVariable(ecb->ConnID, HEADERS[item], buff, pitemlen)) {

			switch (GetLastError())
			{
			case ERROR_INSUFFICIENT_BUFFER:
					{
						_snprintf(msg, 500, "INSUFFICIENT BUFFER for %s<br>", HEADERS[item]);
						log_message(msg);
						break;
					}
			case ERROR_NO_DATA:
					{
						_snprintf(msg, 500,"no data for %s<br>", HEADERS[item]);
						log_message(msg);
						envitem = calloc(sizeof(EnvItem), 1);
						envitem->key = calloc(strlen(HEADERS[item])+1,1);  //this is done to make memory management easier
						memcpy(envitem->key, HEADERS[item], strlen(HEADERS[item]));
						envitem->val = NULL;//buff;
						itemList[item-skipped+httpItemCount] = envitem;
						pitemlen = &itemlen;
						item++;
						break;
					  }
			default:
					{
						_snprintf(msg, 500, "default generate error for %s\n<br>", HEADERS[item]);
						log_message(msg);
						item++;
						skipped++;
						pitemlen = &itemlen;
					}
			}
		}
		else {
					int val_len = strlen(buff);

					_snprintf(msg, 500, "good generate for %s=%s<br>", HEADERS[item], buff);
					log_message(msg);

					envitem = (EnvItem*)calloc(sizeof(EnvItem), 1);
					envitem->key = calloc(strlen(HEADERS[item])+1,1);  //this is done to make memory management easier
					memcpy(envitem->key, HEADERS[item], strlen(HEADERS[item]));
					envitem->val = calloc(sizeof(char),val_len+1);
					memcpy(envitem->val, buff, val_len);
					itemList[item-skipped+httpItemCount]=envitem;
					pitemlen = &itemlen;  //reset
					item++;
			}
		free(buff);
		buff=NULL;
		sprintf(msg, "Freed buffer %i in standard headers section of generateEnvItems with sizeof %i", item, sizeof(buff));
		log_message(msg);

		}


	return itemList;
}

/*********************************************************************
Parse the first part of the data sent by the AppServer
for headers.  Returns a pointer to the start of the actual content.
**********************************************************************/
char* parseHeaders( char* data, LPEXTENSION_CONTROL_BLOCK ecb) {
	int endindex=0;
	int ptrindex=0;
	char unixdblend[] = "\n\n";
	char dosdblend[]= "\r\n\r\n";
	char dosend[]="\r\n";
	char unixend[]="\n";
	int  nlchar = '\n';
	char txtct[] = "Content-type:";
	char txtlocation[]= "Location:";
	char txtstatus[]= "Status:";
	char* endptr=NULL;
	char* status=NULL;
	char* contenttype=NULL;
	char* location=NULL;
	char* otherheaders;
	int dos=1;  //type of line sep
	int lineendindex=0;
	long headerlength=0;
	int otherheadersindex=0;
	HSE_SEND_HEADER_EX_INFO   SendHeaderExInfo;
	char STATUS_OK[] = " 200 OK";    


	if( (endptr = strstr(data, dosdblend)) == NULL) {
		endptr = strstr(data, unixdblend);
		dos=0;
	}
	if (endptr == NULL) return 0;  //couldn't find the end of the headers

	endindex = endptr + strlen(dos?dosdblend:unixdblend) - data;  //the index of the last valid character

//from here on out, we ignore any carriage returns	

	otherheaders = calloc(sizeof(char), endindex+4);

	log_message("Start of raw message->");
	log_message(data);

	while(ptrindex < endindex) {
		lineendindex = strstr((char*)(data+ptrindex), unixend) - (data+ptrindex); //an index into the current value of ptr
		 if ( strnicmp(data+ptrindex, txtstatus, strlen(txtstatus)) == 0) {
			//found status
			log_message("Status text->");
			log_message(data+ptrindex);
			status = data+ptrindex+strlen(txtstatus); // ptr to start of status number (may include a space)	
		}
		else {
 	 		strncat(otherheaders, data+ptrindex, lineendindex + strlen(unixend));
			
		}
		ptrindex = ptrindex + lineendindex + strlen(unixend);
	}

//The dbl newline necessary at the end of otherheaders comes from the appserver
/*
	if(status) {
		char numbers[]="0123456789";
		int length=0;
		ecb->dwHttpStatusCode = atoi(status+strspn(status," ")); //this apparently doesn't matter
		if(status == " " ) status = status+1;
		length = strspn(status, numbers);
		*(status+length) = '\0';
	}

*/

	SendHeaderExInfo.fKeepConn = FALSE;
	if (status !=NULL) {
		int len;
		SendHeaderExInfo.pszStatus = status;
		len = strchr(status, nlchar) - status;
		SendHeaderExInfo.cchStatus = len;
	}
	else {
		SendHeaderExInfo.pszStatus = STATUS_OK;
		SendHeaderExInfo.cchStatus = lstrlen(SendHeaderExInfo.pszStatus);
	}
	SendHeaderExInfo.pszHeader = otherheaders;
	SendHeaderExInfo.cchHeader = lstrlen(SendHeaderExInfo.pszHeader);

	ecb->ServerSupportFunction(ecb->ConnID, HSE_REQ_SEND_RESPONSE_HEADER_EX, &SendHeaderExInfo,NULL,NULL);
        

//	headerlength = strlen(otherheaders);
//	ecb->ServerSupportFunction(ecb->ConnID, HSE_REQ_SEND_RESPONSE_HEADER, status, &headerlength, (unsigned long*)otherheaders);

	free(otherheaders); //I crash if I free this in apache, does this cause IIS to crash?
	return (endptr + (sizeof(char)*strlen(dos?dosdblend:unixdblend))); //am I off by one here? No?
}


/*******************************************************************
Process the reponse from the AppServer

Note: The header must be less than buflen bytes long
********************************************************************/
int processISAPIResponse(int sock, LPEXTENSION_CONTROL_BLOCK ecb) {
  char *buff, *ptr;
  unsigned int buflen = 8092;
  unsigned int br, bs;
  int headersDone = 0;
  char msg[500];

  buff = calloc(buflen,1);
  do {
	br = -1;
	ptr = NULL;
	br = recv(sock, buff, buflen, 0);
	
	log_message( buff );

	if (headersDone==0) {
	//make sure we have all of the headers

		ptr = parseHeaders(buff,ecb);
		if (ptr == NULL) {
			//we're screwed
			return 0;
		}
		bs = br - (ptr - buff);
		headersDone = 1;
	}
	else {
		ptr = buff;
		bs = br;
	}
	ecb->WriteClient(ecb->ConnID, ptr, &bs, HSE_IO_SYNC);
  } while (br > 0);//== buflen);

	free(buff);
	log_message("Freeing response buffer");
	return 1;
}



BOOL WINAPI GetExtensionVersion( HSE_VERSION_INFO* info) {
	
	info->dwExtensionVersion = MAKELONG(HSE_VERSION_MINOR, HSE_VERSION_MAJOR);

	strcpy(info->lpszExtensionDesc, isa_desc);
	return TRUE;
}


DWORD WINAPI HttpExtensionProc( LPEXTENSION_CONTROL_BLOCK ecb) {

	int retval;
	int sock = 0;
	EnvItem** envItems;
	DictHolder* dicts;
	char* addrstr = /*"localhost";//*/ "127.0.0.1";
	int port = 8086;
	unsigned long addr;

	if (DEBUG) staticecb = ecb;

	retval = 0;


	if ( (envItems=generateEnvItems(ecb)) == NULL) 	return HSE_STATUS_ERROR;

	dicts = createDicts(envItems);

	freeEnviron(envItems);


	addr = resolve_host(addrstr);
	log_message("Got addr translation");

	sock = wksock_open(addr, port);

	if (! sendISAPIRequest(sock, dicts, ecb)) return HSE_STATUS_ERROR;

	freeWFILE(dicts->int_dict);
	freeWFILE(dicts->whole_dict);
	free(dicts);

	if ( ! processISAPIResponse(sock, ecb)) return HSE_STATUS_ERROR;

	close(sock);

	return HSE_STATUS_SUCCESS;

 }





