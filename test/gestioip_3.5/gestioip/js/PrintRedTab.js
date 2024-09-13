
function check_not_rooted_checkbox(STRING) {
        if ( document.printredtabheadform.show_endnet.checked == true ) {
                document.printredtabheadform.hide_not_rooted.disabled=false;
		document.getElementById('hide_not_rooted_text').innerHTML=STRING;
        }else{
                document.printredtabheadform.hide_not_rooted.disabled=true;
		document.getElementById('hide_not_rooted_text').innerHTML='<font color="gray">' +  STRING + '<font>';
        }
}

function createCookie(name,value,days)
{
  if (days)
  {
      var date = new Date();
      date.setTime(date.getTime()+(days*24*60*60*1000));
      var expires = "; expires="+date.toGMTString();
  }
  else var expires = "";
  document.cookie = name+"="+value+expires+"; path=/;SameSite=Strict";
}


function readCookie(name)
{
  var nameEQ = name + "=";
  var ca = document.cookie.split(';');
  for(var i=0;i < ca.length;i++)
  {
      var c = ca[i];
      while (c.charAt(0)==' ') c = c.substring(1,c.length);
      if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
  }
  return null;
}


function eraseCookie(name)
{
  createCookie(name,"",-1);
}

function scrollToCoordinates() {
  var x = readCookie('net_scrollx');
  var y = readCookie('net_scrolly');
  window.scrollTo(x, y);
  eraseCookie('net_scrollx')
  eraseCookie('net_scrolly')
}

function saveScrollCoordinates() {
  var x = (document.all)?document.body.scrollLeft:window.pageXOffset;
  var y = (document.all)?document.body.scrollTop:window.pageYOffset;
  createCookie('net_scrollx', x, 0);
  createCookie('net_scrolly', y, 0);
  return;
}

function scrollToTop() {
  var x = '0';
  var y = '0';
  window.scrollTo(x, y);
  eraseCookie('net_scrollx')
  eraseCookie('net_scrolly')
}


function confirmation(NET,TYPE,ROOTNET,TEXT) {
	
        var answer = confirm(NET + ": " + TEXT)

        if (answer){
                return true;
        }else{
                return false;
        }
}

function confirmation_new(NET,TYPE,ROOTNET,TEXT,URL,URL_PARAMS) {
	
        var answer = confirm(NET + ": " + TEXT)

//        var node_id = $('#rootnet_tree').jstree('get_selected').attr('id')
        if ( document.getElementById('rootnet_tree')) {
            var node_id = $('#rootnet_tree').jstree('get_selected');
            var parent_network_id = node_id.toString().replace('root_network_','');
            console.log("conf new NODE ID: " + node_id + " - " + parent_network_id);
            if ( node_id == "tree_all" ) {
                parent_network_id = "";
            }
            console.log("confirmation_new parent_network_id: " + parent_network_id);

            if ( ! URL_PARAMS.match(/parent_network_id/) ) {
                if ( node_id && parent_network_id ) {
                    URL_PARAMS = URL_PARAMS + "&parent_network_id=" + parent_network_id;
                }
            }
        }

        if (answer){
                console.log("confirmation_new: " + URL + " " + URL_PARAMS);
                load_content_net_simple(URL,URL_PARAMS)
//                return true;
        }else{
                return false;
        }
}


function confirmation_mass_update_new(BORRAR,VACIAR,DELETE_CONFIRM,CLEAR_CONFIRM,URL,URL_PARAMS,ANZ_NET) {
      var MESSAGE;
      for (var i=0; i<document.mass_update.mass_action_type.options.length; i++) {
          if (document.mass_update.mass_action_type.options[i].selected == true ) {
			MESSAGE=document.mass_update.mass_action_type.options[i].value;
          }
      }

	  var URL_PARAMS
      for (var i=0; i<=ANZ_NET; i++) {
          var element = document.getElementById("mass_update_red_" + i);
          if (typeof(element) != undefined && element != null) {
            if ( document.getElementById("mass_update_red_" + i).checked == true ) {
                  var NET_ID = document.getElementById("mass_update_red_" + i).value;
                  URL_PARAMS = URL_PARAMS + "&mass_update_red_submit_" + i + "=" + NET_ID;
            } else {
                  URL_PARAMS = URL_PARAMS + "&mass_update_red_submit_" + i + "=";
            }
          }
      }

   console.log("confirmation_mass_update_new MESSAGE: " + MESSAGE);

   var answer = "";
   if (MESSAGE == BORRAR) {
	answer = confirm(DELETE_CONFIRM)
   } else if (MESSAGE == VACIAR) {
	answer = confirm(CLEAR_CONFIRM)
   }

   if (answer){

     MassOnSubmitForm(ANZ_NET);

     $('#mass_update').append('<input type="hidden" name="mass_submit" value="mass_update" />');

     var form = $("#mass_update");
     
     var form_serialized = form.serializeArray();

     console.log("confirmatin_mass_update_new: typeof data" + typeof form_serialized);

     $("#content").load(URL, form_serialized);
   } else {
     return false;
   }
}

function confirmation_mass_update(BORRAR,VACIAR,DELETE_CONFIRM,CLEAR_CONFIRM) {
	console.log("confirmation_mass_update");
      var MESSAGE;
      for (var i=0; i<document.mass_update.mass_action_type.options.length; i++) {
          if (document.mass_update.mass_action_type.options[i].selected == true ) {
		MESSAGE=document.mass_update.mass_action_type.options[i].value;
          }
      }

   if (MESSAGE == BORRAR) {
	answer = confirm(DELETE_CONFIRM)
   } else if (MESSAGE == VACIAR) {
	answer = confirm(CLEAR_CONFIRM)
   }

   if (answer){
     return true;
   } else {
     return false;
   }
}

function changeBM(NETCOUNT) {

for (i=0;i<=NETCOUNT;i++) {
	var NNAME="SMbutton_" + i
        var str=document.getElementById(NNAME).innerHTML;
	var patt = /^\d{1,2}$/
	var RES=patt.test(str)
	if (  RES == true ) {
                var n=str.
                replace(/^8$/,"255.0.0.0 ").
                replace(/^9$/,"255.128.0.0 ").
                replace(/^10$/,"255.192.0.0 ").
                replace(/^11$/,"255.224.0.0 ").
                replace(/^12$/,"255.240.0.0 ").
                replace(/^13$/,"255.248.0.0 ").
                replace(/^14$/,"255.252.0.0 ").
                replace(/^15$/,"255.254.0.0 ").
                replace(/^16$/,"255.255.0.0 ").
                replace(/^17$/,"255.255.128.0 ").
                replace(/^18$/,"255.255.192.0 ").
                replace(/^19$/,"255.255.224.0 ").
                replace(/^20$/,"255.255.240.0 ").
                replace(/^21$/,"255.255.248.0 ").
                replace(/^22$/,"255.255.252.0 ").
                replace(/^23$/,"255.255.254.0 ").
                replace(/^24$/,"255.255.255.0 ").
                replace(/^25$/,"255.255.255.128 ").
                replace(/^26$/,"255.255.255.192 ").
                replace(/^27$/,"255.255.255.224 ").
                replace(/^28$/,"255.255.255.240 ").
                replace(/^29$/,"255.255.255.248 ").
                replace(/^30$/,"255.255.255.252 ").
                replace(/^31$/,"255.255.255.254 ").
                replace(/^32$/,"255.255.255.255 ");
} else {
                var n=str.
                replace("255.0.0.0 ","8").
                replace("255.128.0.0 ","9").
                replace("255.192.0.0 ","10").
                replace("255.224.0.0 ","11").
                replace("255.240.0.0 ","12").
                replace("255.248.0.0 ","13").
                replace("255.252.0.0 ","14").
                replace("255.254.0.0 ","15").
                replace("255.255.0.0 ","16").
                replace("255.255.128.0 ","17").
                replace("255.255.192.0 ","18").
                replace("255.255.224.0 ","19").
                replace("255.255.240.0 ","20").
                replace("255.255.248.0 ","21").
                replace("255.255.252.0 ","22").
                replace("255.255.254.0 ","23").
                replace("255.255.255.0 ","24").
                replace("255.255.255.128 ","25").
                replace("255.255.255.192 ","26").
                replace("255.255.255.224 ","27").
                replace("255.255.255.240 ","28").
                replace("255.255.255.248 ","29").
                replace("255.255.255.252 ","30").
                replace("255.255.255.254 ","31").
                replace("255.255.255.255 ","32");
}
        document.getElementById(NNAME).innerHTML=n;
        }
}
