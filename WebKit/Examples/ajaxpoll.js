/*
	Extended Ajax Javascript functions used by AjaxPage.

	Implements a periodic polling mechanism to prevent server timeouts
	and to allow pushing commands from the server to the client.

	Written by John Dickinson based on ideas from
	Apple Developer Connection and DivMod Nevow.
	Some changes made by Christoph Zwerschke.
*/

var dying = false;
var poll_requester = getRequester();

function openPollConnection()
{
	if (poll_requester)
	{
		var req = poll_requester;
		req.onreadystatechange = function() {
			var wait = 3 + Math.random() * 5; // 3 - 8 seconds
			if (req.readyState == 4) {
				if (req.status == 200) {
					try {
						eval(req.responseText);
						req.abort();
					} catch(e) {
						; // ignore errors
					}
					if (!dying) {
						// reopen the response connection after a wait period
						setTimeout("openPollConnection()", wait*1000);
					}
				}
			}
		}
		var url = request_url + 'Poll&_req_=' + ++request_id;
		req.open("GET", url, true);
		req.send(null);
	}
}

function shutdown()
{
	if (poll_requester) {
		poll_requester.abort();
	}
	dying = true;
}

var userAgent = navigator.userAgent.toLowerCase()
if (userAgent.indexOf("msie") >= 0) {
	// IE specific
	window.attachEvent("onbeforeunload", shutdown);
} else if (document.implementation && document.implementation.createDocument) {
	// Mozilla specific (onbeforeunload is in v1.7+ only)
	window.addEventListener("beforeunload", shutdown, false);
}

// Open initial connection back to server:
openPollConnection();
