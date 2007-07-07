/*
	Basic Ajax Javascript functions used by AjaxPage.

	Written by John Dickinson based on ideas from
	Apple Developer Connection and DivMod Nevow.
	Some changes made by Christoph Zwerschke.
*/

var request_url = document.location.toString();
if (request_url.indexOf('?') >= 0) {
	request_url = request_url.substr(0, request_url.indexOf('?'));
}
request_url += "?_action_=ajax"
var request_id = 0;

function getRequester() {
	if (window.XMLHttpRequest) {
		try {
			req = new XMLHttpRequest();
		} catch(e) {
			req = false;
		}
	} else if(window.ActiveXObject) { // IE specific
		try {
			req = new ActiveXObject("Msxml2.XMLHTTP");
		} catch(e) {
			try {
				req = new ActiveXObject("Microsoft.XMLHTTP");
			} catch(e) {
				req = false;
			}
		}
	}
	return req
}

function openConnection(req, url)
{
	if (req) {
		req.onreadystatechange = function() {
			if (req.readyState == 4) {
				if (req.status == 200) {
					try {
						eval(req.responseText);
						req.abort();
						delete req;
					} catch (e) {
						; // ignore errors
					}
				}
			}
		};
		req.open("GET", url, true);
		req.send(null);
	}
}

// Generic Ajax call:
function ajax_call(pre_action, call) {
	if (pre_action) {
		eval(pre_action);
	}
	var args = '&_req_=' + ++request_id;
	for (i=2; i<arguments.length; i++) {
		args += '&_=' + encodeURIComponent(arguments[i])
	}
	req = getRequester();
	if (req) {
		openConnection(req, request_url + "Call&_call_=" + call + args);
	}
}

// Ajax call specific to forms:
function ajax_call_form(call, form, dest, val) {
	if (dest) {
		ajax_setTag(dest, val);
	}
	var values = Array();
	for (i=0; i<form.elements.length; i++) {
		var e = form.elements[i];
		name = e.name;
		if (!(((e.type == 'checkbox') || (e.type == 'radio')) && (!e.checked))) {
			values[i] = [name, e.value];
		}
	}
	var args = '&_req_=' + ++request_id;
	for (i=0; i<values.length; i++) {
		args += '&_=' + encodeURIComponent(values[i])
	}
	req = getRequester();
	if (req) {
		openConnection(req, request_url + "Call&_call_=" + call + args);
	}
}

// Some Ajax helper functions:

function ajax_setTag(which, val) {
	var e = document.getElementById(which);
	e.innerHTML = val;
}

function ajax_setClass(which, val) {
	var e = document.getElementById(which);
	e.className = val;
}

function ajax_setID(which, val) {
	var e = document.getElementById(which);
	e.id = val;
}

function ajax_setValue(which, val) {
	var e = document.getElementById(which);
	e.value = val;
}

function ajax_setReadonly(which, val) {
	var e = document.getElementById(which);
	if (val) {
		e.setAttribute('readonly', 'readonly');
	}
	else {
		e.removeAttribute('readonly');
	}
}
