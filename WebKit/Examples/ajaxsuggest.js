/*
	Javascript for the AjaxSuggest example.

	Provides all the client-side heavy lifting required to get Ajax functionality into a web page.

	Coded by Ryan Smith (www.dynamicajax.com/fr/AJAX_Suggest_Tutorial-271_290_312.html).
	Adapted for Webware by Robert Forkel.
*/

// Function that is called after the page has been loaded:
function initPage() {
	document.getElementById('query').focus()
}

// Function to be associated with input control (initiates the Ajax request):
function getSuggestions() {
	ajax_call(false, 'suggest', escape(document.getElementById('query').value));
}

// Function handling the Ajax response:
function handleSuggestions(res) {
	if (res.length > 0) {
		var e = document.getElementById('suggestions');
		e.innerHTML = '<div onmouseover="suggestOver(this)" onmouseout="suggestOut(this)" onclick="clearSuggestions()" class="suggest_button_normal">close</div>';
		for (i=0; i<res.length; i++) {
            e.innerHTML += '<div onmouseover="suggestOver(this)" onmouseout="suggestOut(this)" onclick="setQuery(this.innerHTML)" class="suggest_link_normal">' + res[i] + '</div>';
		}
		e.className = 'show';
	} else {
		clearSuggestions();
	}
}

function suggestOver(div_node) {
	div_node.className = div_node.className.replace('_normal', '_over');
}

function suggestOut(div_node) {
	div_node.className = div_node.className.replace('_over', '_normal');
}

function clearSuggestions() {
	var e = document.getElementById('suggestions')
	e.innerHTML = '';
	e.className = 'hide'
}

function setQuery(value) {
	document.getElementById('query').value = value;
	clearSuggestions();
}
