
function clear_div_notify() {
    console.log("clear_div_notify");
    var element = document.getElementById('NotifyText');
    if (typeof(element) != 'undefined' && element != null) {
		console.log("clear_div_notify FOUND: " + document.getElementById('NotifyText').innerHtml);
		document.getElementById('NotifyText').innerHtml="";
	}
}


function scrollFunction() {
  if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
	document.getElementById("go_to_top_btn").style.display = "block";
	document.getElementById("go_to_bottom_btn").style.display = "block";
  } else {
	document.getElementById("go_to_top_btn").style.display = "none";
	document.getElementById("go_to_bottom_btn").style.display = "none";
  }
}

// When the user clicks on the button, scroll to the top of the document
function topFunction(DIR) {
  if ( DIR == "top" ) {
	  document.body.scrollTop = 0; // For Safari
	  document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
  } else {
//	  var element = document.getElementById('bottom-row');
//	  element.scrollTop = element.scrollHeight - element.clientHeight;
	window.scrollTo(0,document.body.scrollHeight);
  }
}

function setCookie(cname, cvalue, exdays) {
  var d = new Date();
  d.setTime(d.getTime() + (exdays*24*60*60*1000));
  var expires = "expires="+ d.toUTCString();
  document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/;SameSite=Strict";
}

function create_rootnet_chain(CHAIN) {
	document.getElementById("rootnet_chain").innerHTML=CHAIN;
}

function create_pages_links_net(PAGES_LINKS) {
    console.log("create_pages_links_net");
//    var element =  document.getElementById('elementId');
    var element =  document.getElementById('pages_links_net');
    if (typeof(element) != 'undefined' && element != null)
    {
      // exists.
      document.getElementById("pages_links_net").innerHTML=PAGES_LINKS;
    }
}

function reset_form(NAME, URL) {
    document.getElementById(NAME).reset();

	IP_VERSION_ELE = getCookie("IPVersionEle");

	var I;
	if ( IP_VERSION_ELE == "v6" ) {
		I=2
	} else {
		I=1
	}
	e = document.printredtabheadform.ip_version_ele;
	e.selectedIndex = I;

    console.log("IP_VERSION_ELE: " + IP_VERSION_ELE + ", INDEX: " + I);

	document.printredtabheadform.loc_ele.disabled = false;
	document.printredtabheadform.tipo_ele. disabled = false;

	URL = URL + '&ip_version_ele=' + IP_VERSION_ELE;
	console.log("URL2: " + URL);

    URL_LOAD_ENCODED = encodeURI(URL)
    console.log("reset_form: " + URL_LOAD_ENCODED)

    $("#content").load(URL_LOAD_ENCODED);
}

function setCookie(name,value,days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days*24*60*60*1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/;SameSite=Strict";
}

function getCookie(cname) {
  var name = cname + "=";
  var decodedCookie = decodeURIComponent(document.cookie);
  var ca = decodedCookie.split(';');
  for(var i = 0; i <ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return "";
}


function eraseCookie(name) {   
    document.cookie = name+'=; Max-Age=-99999999;';  
}


function update_nav_text(TEXT) {
    console.log("text: " + TEXT);
    document.getElementById('nav_text').innerHTML=TEXT;
}

function hideIntervalDetail(VALUE) {
    console.log("hideIntervalDetail: " + VALUE);
    if ( VALUE == 1 ) {
        document.getElementById("interval_day_of_week").style.display = "none";
        document.getElementById("before_text_interval_day_of_week").style.display = "none";
        document.getElementById("interval_months").style.display = "none";
        document.getElementById("before_text_interval_months").style.display = "none";
        document.getElementById("interval_day_of_month").style.display = "none";
//        document.getElementById("hint_text_interval_day_of_month").style.display = "none";
        document.getElementById("before_text_interval_day_of_month").style.display = "none";
    } else if ( VALUE == 2 ) {
        document.getElementById("interval_day_of_week").style.display = "inline";
        document.getElementById("before_text_interval_day_of_week").style.display = "inline";
        document.getElementById("interval_months").style.display = "none";
        document.getElementById("before_text_interval_months").style.display = "none";
        document.getElementById("interval_day_of_month").style.display = "none";
        document.getElementById("before_text_interval_day_of_month").style.display = "none";
    } else if ( VALUE == 3 ) {
        document.getElementById("interval_day_of_week").style.display = "none";
        document.getElementById("before_text_interval_day_of_week").style.display = "none";
        document.getElementById("interval_months").style.display = "inline";
        document.getElementById("before_text_interval_months").style.display = "inline";
        document.getElementById("interval_day_of_month").style.display = "inline";
        document.getElementById("before_text_interval_day_of_month").style.display = "inline";
    }
}

function disableJobInterval(VALUE) {
  var y = document.getElementById("run_once").checked;
  var e = document.getElementById("interval");
  if ( y == true ) {
      if (typeof(e) != 'undefined' && e != null) {
          document.getElementById("interval").disabled = true;
          document.getElementById("interval_minutes").disabled = true;
          document.getElementById("interval_hours").disabled = true;
          document.getElementById("interval_day_of_month").disabled = true;
          document.getElementById("interval_months").disabled = true;
          document.getElementById("interval_day_of_week").disabled = true;
          clearSelected("interval");
          clearSelected("interval_minutes");
          clearSelected("interval_hours");
          clearSelected("interval_day_of_month");
          clearSelected("interval_months");
          clearSelected("interval_day_of_week");
          document.getElementById("execution_time").disabled = false;
          document.getElementById("execution_time").value = VALUE;
      }
    } else {
      if (typeof(e) != 'undefined' && e != null) {
          document.getElementById("interval").disabled = false;
          document.getElementById("interval_minutes").disabled = false;
          document.getElementById("interval_hours").disabled = false;
          document.getElementById("interval_day_of_month").disabled = false;
          document.getElementById("interval_months").disabled = false;
          document.getElementById("interval_day_of_week").disabled = false;
          document.getElementById("execution_time").disabled = true;
      }
    }
}

function disableIntDescIdent(VALUE) {
  console.log("disableIntDescIdent value:" + VALUE)
  var y = document.getElementById("add_if_descr").checked;
  if ( y == true ) {
      console.log("disableIntDescIdent: true")
      document.getElementById("interface_descr_ident").disabled = false;
  } else {
      console.log("disableIntDescIdent: false")
      document.getElementById("interface_descr_ident").disabled = true;
  }
}

function disableNodesFields(VALUE){
    console.log("disableNodesFields:" + VALUE);
    if ( VALUE == "nodes_list" ) {
      document.getElementById("CSV_nodes").disabled = false;
      document.getElementById("nodes_file").disabled = true;
      document.getElementById("use_tags").disabled = true;
    } else if ( VALUE == "nodes_file" ) {
      document.getElementById("CSV_nodes").disabled = true;
      document.getElementById("nodes_file").disabled = false;
      document.getElementById("use_tags").disabled = true;
    } else if ( VALUE == "use_tags" ) {
      document.getElementById("CSV_nodes").disabled = true;
      document.getElementById("nodes_file").disabled = true;
      document.getElementById("use_tags").disabled = false;
    }
}

function disableNodesFieldsHost(VALUE){
    console.log("disableNodesFields:" + VALUE);
    e = document.getElementById("use_range");
    t = document.getElementById("use_tags");
    if ( VALUE == "network_list" ) {
      document.getElementById("CSV_networks").disabled = false;
      document.getElementById("networks_file").disabled = true;
      if (typeof(t) != 'undefined' && t != null) {
        document.getElementById("use_tags").disabled = true;
      }
      document.getElementById("location_scan").disabled = true;
      if (typeof(e) != 'undefined' && e != null) {
        document.getElementById("use_range").disabled = true;
      }
    } else if ( VALUE == "networks_file" ) {
      document.getElementById("CSV_networks").disabled = true;
      document.getElementById("networks_file").disabled = false;
      if (typeof(t) != 'undefined' && t != null) {
        document.getElementById("use_tags").disabled = true;
      }
      document.getElementById("location_scan").disabled = true;
      if (typeof(e) != 'undefined' && e != null) {
        document.getElementById("use_range").disabled = true;
      }
    } else if ( VALUE == "use_tags" ) {
      document.getElementById("CSV_networks").disabled = true;
      document.getElementById("networks_file").disabled = true;
      if (typeof(t) != 'undefined' && t != null) {
        document.getElementById("use_tags").disabled = false;
      }
      document.getElementById("location_scan").disabled = true;
      if (typeof(e) != 'undefined' && e != null) {
        document.getElementById("use_range").disabled = true;
      }
    } else if ( VALUE == "use_locations" ) {
      document.getElementById("CSV_networks").disabled = true;
      document.getElementById("networks_file").disabled = true;
      if (typeof(t) != 'undefined' && t != null) {
        document.getElementById("use_tags").disabled = true;
      }
      document.getElementById("location_scan").disabled = true;
      if (typeof(e) != 'undefined' && e != null) {
        document.getElementById("use_range").disabled = true;
      }
    } else if ( VALUE == "use_range" ) {
      document.getElementById("CSV_networks").disabled = true;
      document.getElementById("networks_file").disabled = true;
      if (typeof(t) != 'undefined' && t != null) {
        document.getElementById("use_tags").disabled = true;
      }
      document.getElementById("use_range").disabled = false;
      document.getElementById("location_scan").disabled = true;
    } else if ( VALUE == "location_scan" ) {
      document.getElementById("CSV_networks").disabled = true;
      document.getElementById("networks_file").disabled = true;
      if (typeof(t) != 'undefined' && t != null) {
        document.getElementById("use_tags").disabled = true;
      }
      document.getElementById("location_scan").disabled = false;
      if (typeof(e) != 'undefined' && e != null) {
        document.getElementById("use_range").disabled = true;
      }
    }
}

function clearSelected(SELECT){
var elements = document.getElementById(SELECT).options;

for(var i = 0; i < elements.length; i++){
  elements[i].selected = false;
}
}


function load_content_net_freerange(URL, CLIENT_ID) {

  console.log("load_content_net_freerange: " + URL);

  var SCRIPT;
  var e;
  var c;
  var y = document.getElementById("show_free_ranges").checked;
  if ( y == true ) {
      console.log("checked");
      SCRIPT = "ip_show_free_range_nohead.cgi";

      e = document.getElementById("loc_ele");
      e.selectedIndex = 0 
      e.disabled = true;

      e = document.getElementById("tipo_ele");
      e.selectedIndex = 0 
      e.disabled = true;

      e = document.getElementById("show_rootnet"); 
      e.disabled = true;

      e = document.getElementById("show_endnet"); 
      e.disabled = true;
  } else {
      console.log("unchecked");
      SCRIPT = "index_nohead.cgi";

      e = document.getElementById("loc_ele");
      c = getCookie("loc_ele");
      e.value = c;
      e.disabled = false;

      e = document.getElementById("tipo_ele");
      c = getCookie("tipo_ele");
      e.value = c;
      e.disabled = false;

      e = document.getElementById("show_rootnet"); 
      c = getCookie("ShowRootNet");
      if ( c == 1 ) {
        e.checked = true;
      } else {
        e.checked = false;
      }
      e.disabled = false;

      e = document.getElementById("show_endnet"); 
      c = getCookie("ShowEndNet");
      if ( c == 1 ) {
        e.checked = true;
      } else {
        e.checked = false;
      }
      e.disabled = false;
  }

  var ENTRIES_PER_PAGE = "";
  e = document.getElementById("entries_per_page");
  if (typeof(e) != 'undefined' && e != null) {
      ENTRIES_PER_PAGE = e.options[e.selectedIndex].value;
      console.log(ENTRIES_PER_PAGE);
      setCookie("EntriesRedPorPage", ENTRIES_PER_PAGE, 365);
  }

//  e = document.getElementById("ip_version_ele");
//  IP_VERSION_ELE = e.options[e.selectedIndex].value;

  var IP_VERSION_ELE = "";
  e = document.getElementById("ip_version_ele");
  if ( e.type == "hidden" ) {
      IP_VERSION_ELE = e.value;
  } else {
      IP_VERSION_ELE = e.options[e.selectedIndex].value;
      console.log(IP_VERSION_ELE);
  }
  setCookie("IPVersionEle", IP_VERSION_ELE, 365);

  COLLAPSE_ROOTNET = "create";
  var x = document.getElementById("hide_not_rooted").checked; 
  console.log(x);
  if ( x == true ) {
	  setCookie("HideNotRootedNet", 1, 90)
  } else {
	  setCookie("HideNotRootedNet", 0, 90)
      COLLAPSE_ROOTNET = "";
  }

  PARAMS_DYN="?ip_version_ele=" + IP_VERSION_ELE + "&hide_not_rooted=" + COLLAPSE_ROOTNET + "&client_id=" + CLIENT_ID + "&entries_per_page=" + ENTRIES_PER_PAGE;

  var z = document.getElementById("tree_selected_rootnet");
  if (typeof(z) != 'undefined' && z != null) {
      var tree_selected_rootnet_value=document.getElementById("tree_selected_rootnet").value;
      console.log("tree_selected_rootnet_value: " + tree_selected_rootnet_value);
      if ( tree_selected_rootnet_value ) {
          PARAMS_DYN=PARAMS_DYN + "&rootnet=y&red_num=" + tree_selected_rootnet_value;
      }
  }

  URL_LOAD = URL + SCRIPT + PARAMS_DYN

  URL_LOAD_ENCODED = encodeURI(URL_LOAD)
  console.log("url encoded: " + URL_LOAD_ENCODED);

  $("#content").load(URL_LOAD);
}


function load_content_net_no_dyn_param(URL, PARAMS) {
  URL_LOAD = URL + "?" + PARAMS

  URL_LOAD_ENCODED = encodeURI(URL_LOAD)
  console.log("load_content_net_no_dyn_param:" + URL_LOAD_ENCODED);

  $("#Inhalt").load(URL_LOAD_ENCODED);
}



function load_content_net_simple(URL, PARAMS) {
    console.log("LOAD CONTENT NET SIMPLE");

//  e = document.getElementById("ip_version_ele");
//  IP_VERSION_ELE = e.options[e.selectedIndex].value;

  var PARAMS_DYN = "?";
//  if ( ! PARAMS.includes("parent_network_id")) {
      var IP_VERSION_ELE = "";
      e = document.getElementById("ip_version_ele");
      if ( e.type == "hidden" ) {
          IP_VERSION_ELE = e.value;
      } else {
          IP_VERSION_ELE = e.options[e.selectedIndex].value;
          console.log(IP_VERSION_ELE);
      }

      var LOC_ELE = "";
      var LOC_ELE_PARAM = "";
      e = document.getElementById("loc_ele");
      if (typeof(e) != 'undefined' && e != null) {
		  LOC_ELE = e.options[e.selectedIndex].value;
          LOC_ELE_PARAM = '&loc_ele=' + LOC_ELE;
      }

      var CAT_ELE = "";
      var CAT_ELE_PARAM = "";
      e = document.getElementById("tipo_ele");
      if (typeof(e) != 'undefined' && e != null) {
          CAT_ELE = e.options[e.selectedIndex].value;
          CAT_ELE_PARAM = '&tipo_ele=' + CAT_ELE;
      }

      var ENTRIES_PER_PAGE_ELE = "";
      var ENTRIES_PER_PAGE_ELE_PARAM = "";
      e = document.getElementById("entries_per_page");
      if (typeof(e) != 'undefined' && e != null) {
          ENTRIES_PER_PAGE_ELE = e.options[e.selectedIndex].value;
          ENTRIES_PER_PAGE_ELE_PARAM = '&entries_per_page_ele=' + ENTRIES_PER_PAGE_ELE;
      }

      PARAMS_DYN="?ip_version_ele=" + IP_VERSION_ELE + LOC_ELE_PARAM + CAT_ELE_PARAM + ENTRIES_PER_PAGE_ELE_PARAM;
//      PARAMS_DYN="?ip_version_ele=" + IP_VERSION_ELE + "&loc_ele=" + LOC_ELE + "&tipo_ele=" + CAT_ELE + "&entries_per_page=" + ENTRIES_PER_PAGE_ELE;

//  } else {
//      console.log("PARAMS REPLACE1: " + PARAMS);
//      PARAMS = PARAMS.replace(/^&/,"");
//      console.log("PARAMS REPLACE2: " + PARAMS);
//  }

  URL_LOAD = URL + PARAMS_DYN + PARAMS

  URL_LOAD_ENCODED = encodeURI(URL_LOAD)
  console.log("load_content_net_simple:" + URL_LOAD_ENCODED);

  $("#content").load(URL_LOAD_ENCODED);
}






function load_content_net(URL, CLIENT_ID, I_PARAMS_DYN) {
    console.log("LOAD CONTENT NET");

  var SCRIPT;
  var e;

//  e = document.getElementById("ip_version_ele");
//  IP_VERSION_ELE = e.options[e.selectedIndex].value;

  var IP_VERSION_ELE = "";
  e = document.getElementById("ip_version_ele");
  if (typeof(e) != 'undefined' && e != null) {
      if ( e.type == "hidden" ) {
          IP_VERSION_ELE = e.value;
      } else {
          IP_VERSION_ELE = e.options[e.selectedIndex].value;
          console.log(IP_VERSION_ELE);
      }
      setCookie("IPVersionEle", IP_VERSION_ELE, 365);
  } else {
    IP_VERSION_ELE = getCookie("ip_version_ele");

  }

  var LOC_ELE = "";
  e = document.getElementById("loc_ele");
  console.log("load_content_net LOC ELE: " + e)
  if (typeof(e) != 'undefined' && e != null) {
      LOC_ELE = e.options[e.selectedIndex].value;
      setCookie("loc_ele", LOC_ELE, 365)
  } else {
    LOC_ELE = getCookie("loc_ele");
  }

  var CAT_ELE = "";
  e = document.getElementById("tipo_ele");
  if (typeof(e) != 'undefined' && e != null) {
      CAT_ELE = e.options[e.selectedIndex].value;
      setCookie("tipo_ele", CAT_ELE, 365)
  } else {
    CAT_ELE = getCookie("cat_ele");
  }

  var SHOW_ROOTNET = "create";
  e = document.getElementById("show_rootnet");
  if (typeof(e) != 'undefined' && e != null) {
      var x = document.getElementById("show_rootnet").checked; 
      if ( x == true ) {
          setCookie("ShowRootNet", 1, 90)
      } else {
          setCookie("ShowRootNet", 0, 90)
          SHOW_ROOTNET = "";
      }
  } else {
    SHOW_ROOTNET = getCookie("show_rootnet");
  }

  var SHOW_ENDNET = "create";
  e = document.getElementById("show_endnet");
  if (typeof(e) != 'undefined' && e != null) {
      var x = document.getElementById("show_endnet").checked; 
      if ( x == true ) {
          setCookie("ShowEndNet", 1, 90)
      } else {
          setCookie("ShowEndNet", 0, 90)
          SHOW_ENDNET = "";
      }
  } else {
    SHOW_ENDNET = getCookie("show_endnet");
  }

  var COLLAPSE_ROOTNET = "create";
  if ( IP_VERSION_ELE == "v4" ) {
      document.getElementById("hide_not_rooted").disabled = false;
      e = document.getElementById("hide_not_rooted");
      if (typeof(e) != 'undefined' && e != null) {
          var x = document.getElementById("hide_not_rooted").checked; 
          if ( x == true ) {
              setCookie("HideNotRootedNet", 1, 90)
          } else {
              setCookie("HideNotRootedNet", 0, 90)
              COLLAPSE_ROOTNET = "";
          }
      } else {
        COLLAPSE_ROOTNET = getCookie("collapse_rootnet");
      }
  } else {
      document.getElementById("hide_not_rooted").checked = false;
      document.getElementById("hide_not_rooted").disabled = true;
  }

  var ENTRIES_PER_PAGE_ELE = "";
  e = document.getElementById("entries_per_page");
  if (typeof(e) != 'undefined' && e != null) {
      ENTRIES_PER_PAGE_ELE = e.options[e.selectedIndex].value;
      setCookie("EntriesRedPorPage", ENTRIES_PER_PAGE_ELE, 365)
  }

  // Create URL
  e = document.getElementById("hide_not_rooted");
  if (typeof(e) != 'undefined' && e != null) {
      var y = document.getElementById("show_free_ranges").checked;
      if ( y == false ) {
        SCRIPT = "index_nohead.cgi";
        PARAMS_DYN="?ip_version_ele=" + IP_VERSION_ELE + "&loc_ele=" + LOC_ELE + "&tipo_ele=" + CAT_ELE + "&show_rootnet=" + SHOW_ROOTNET + "&show_endnet=" + SHOW_ENDNET + "&hide_not_rooted=" + COLLAPSE_ROOTNET + "&client_id=" + CLIENT_ID + "&entries_per_page=" + ENTRIES_PER_PAGE_ELE;
      } else {
        SCRIPT = "ip_show_free_range_nohead.cgi";
        PARAMS_DYN="?ip_version_ele=" + IP_VERSION_ELE + "&hide_not_rooted=" + COLLAPSE_ROOTNET + "&client_id=" + CLIENT_ID + "&entries_per_page=" + ENTRIES_PER_PAGE_ELE;
      }
  } else {
        SCRIPT = "index_nohead.cgi";
        PARAMS_DYN="?ip_version_ele=" + IP_VERSION_ELE + "&loc_ele=" + LOC_ELE + "&tipo_ele=" + CAT_ELE + "&show_rootnet=" + SHOW_ROOTNET + "&show_endnet=" + SHOW_ENDNET + "&hide_not_rooted=" + COLLAPSE_ROOTNET + "&client_id=" + CLIENT_ID + "&entries_per_page=" + ENTRIES_PER_PAGE_ELE;
  }

//  URL_LOAD = URL + PARAMS_DYN 
  if ( ! I_PARAMS_DYN ) {
      I_PARAMS_DYN = "";
  }
  URL_LOAD = URL + SCRIPT + PARAMS_DYN + I_PARAMS_DYN

  URL_LOAD_ENCODED = encodeURI(URL_LOAD)
  console.log("load_content_net:" + URL_LOAD_ENCODED);

  $("#content").load(URL_LOAD_ENCODED);
}



function load_client(VAR,URL) {
	CLIENT_ID=VAR.value;
	window.location.href = URL + CLIENT_ID;
}

function load_url(URL) {
    console.log("url: " + URL);
	window.location.href = URL;
}

//http://jsfiddle.net/Zmf6t/
$("#ip_version_ele").change();

function change_select_color(VAR) {
    if($(VAR).val() == "") $(VAR).addClass("empty");
    else $(VAR).removeClass("empty")
    console.log("change_select_color");
}

$("#loc_ele").change();
