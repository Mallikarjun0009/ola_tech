
var DEBUG = "";
var NO_RELOAD_TABLE_SET = "";

$(document).ready(function (){
    console.log( "Tree: ready" );
    var VALUE = getCookie("CollapseSitebar");
    if ( VALUE != "collapse" ) {
        load_jstree();
    }
});


function load_jstree(REFRESH, NO_RELOAD_TABLE) {

  console.log("REFRESH: " + REFRESH);

  if ( NO_RELOAD_TABLE ) {
      NO_RELOAD_TABLE_SET = 1;
  }

  var CLIENT_ID = document.quick_search.client_id.value;

  console.log("NO_RELOAD_TABLE: " + NO_RELOAD_TABLE + " - NO_RELOAD_TABLE_SET: " + NO_RELOAD_TABLE_SET);

  var IP_VERSION = "";
  e = document.getElementById("ip_version_ele");
  if ( e ) {
  if ( e.type == "hidden" ) {
      IP_VERSION = e.value;
  } else {
      IP_VERSION = e.options[e.selectedIndex].value;
      console.log(IP_VERSION + ' - ' + REFRESH);
  }
  }


$.getJSON( "/gestioip/intapi.cgi?request_type=listNetworks&client_name=" + CLIENT_ID + "&output_type=json&no_csv=yes&network_type=root&ip_version=" + IP_VERSION, function() {
})
    .done(function(data) {
        var tree_data = [];

        console.log( "Tree: Success: GET /gestioip/intapi.cgi?request_type=listNetworks&client_name=" + CLIENT_ID + "&output_type=json&no_csv=yes&network_type=root&ip_version=" + IP_VERSION );

        $.each( data, function( key, val ) {
        console.log( "Tree: KEY: " + key + " " + val );
            if ( key == "listNetworksResult" ) {
                var dict = {};
                l2 = []
                $.each( val, function( key2, val2 ) {

                if ( key2 == "NetworkList" ) {
                    console.log( "Tree2: : " + key2 + " " + val2 );
                    var dict2 = {};
                    l2_2 = []
                    $.each( val2, function( key3, val3 ) {

                    if ( key3 == "Network" ) {
                        var i;
						for (i = 0; i < val3.length; i++) { 

                        $.each( val3[i], function( key4, val4 ) {

                            if ( key4 == "rootnet" ) {
                                console.log( "Tree4: : " + key4 + " " + val3[i].IP + " - " + val3[i].rootnet + " - " + val3[i].parent_network_id );

                                // Create a dict of rootnetworks with id as key
                                // val2 is the network object
                                p0_id = val3[i].id
                                if ( p0_id ) {

                                    tree_selected_rootnet_value=p0_id;

                                    var tree_id = "root_network_" + val3[i].id;
                                    var parent_id = "";
                                    var site = val3[i].site;
                                    var descr = val3[i].descr;
                                    var cat = val3[i].cat;
                                    if ( typeof val3[i].parent_network_id === 'undefined' || val3[i].parent_network_id == null || val3[i].parent_network_id == 0) {
                                        parent_id = '#';
                                    } else {
                                        parent_id = "root_network_" + val3[i].parent_network_id;
                                    }
                                    var text = val3[i].IP + "/" + val3[i].BM;

                                    console.log("ID: " + tree_id + " - PARENT ID: " + parent_id + " - TEXT: " + text + " - id: " + p0_id + "SITE: " + site);

                                    tree_data.push({ "id" : tree_id, "parent" : parent_id, "text" : text, "a_attr": {title: descr + " - " + site + " - " + cat} });
                                }
                            }
                         })
                        }
                      }
                    })
                }    
                });

                if ( REFRESH ) {

					//select_node.jstree will be triggered for each childnode if the currently selected node has children.
					//this function stops this behaviour
					//other option: deselect items before reload
					var tree = $('#rootnet_tree').jstree(true);
					tree.refresh(false, function (state) {
						console.dir(state);
						state.core.selected = [];
						return state;
					});
                    console.log("TREE: NO_RELOAD_TABLE_SET: " + NO_RELOAD_TABLE_SET); 
                    $('#rootnet_tree').jstree(true).settings.core.data = tree_data;
                    $('#rootnet_tree').jstree("refresh");
                } else {

                    var $root = $('#rootnet_tree').jstree({ 'core' : {
                        check_callback: true,
                        "themes":{
                            "icons":false,
    //                        "dots": false,
//                            "variant" : "small"
                            "responsive": true

                        },
                        "plugins" : [ "state" ],
                        'data' : tree_data
                    }
                    })


                    // create All tree node
                    $root.jstree('create_node', '#', {'id' : 'tree_all', 'text' : 'ALL'}, 'first');
    //                $root.jstree(true).open_all();
                }
            }
        });
    })

  .fail(function (jqXHR, textStatus, errorThrown){
            // Log the error to the console
       console.log(
           "GET failed: "+
                textStatus, errorThrown, jqXHR.responseText
      )
  })

  .always(function() {
            console.log( "complete" );
  })

$('#rootnet_tree').bind("select_node.jstree", function (e, data) {
    var children = $("#rootnet_tree").jstree(true).get_json(data.node.id, { flat: true });
    var node_id = data.node.id;
	var id = node_id.replace('root_network_','');
    if ( id == "tree_all" ) {
        id = "";
    }
	console.log("RELOAD!!!!! NODE ID: " + node_id + "ID: " + id);
    console.log("NO_RELOAD_TABLE_SETA: " + NO_RELOAD_TABLE_SET)


    var f = document.getElementById("tree_selected_rootnet");
    if (typeof(f) != 'undefined' && f != null) {
        document.getElementById("tree_selected_rootnet").value=id;
    }


  var e;

//  e = document.getElementById("ip_version_ele");
//  IP_VERSION_ELE = e.options[e.selectedIndex].value;

  var IP_VERSION_ELE = "";
  e = document.getElementById("ip_version_ele");
  if ( e.type == "hidden" ) {
      IP_VERSION_ELE = e.value;
  } else {
      IP_VERSION_ELE = e.options[e.selectedIndex].value;
      console.log(IP_VERSION_ELE + ' - ' + REFRESH);
  }

  e = document.getElementById("loc_ele");
  LOC_ELE = e.options[e.selectedIndex].value;

  e = document.getElementById("tipo_ele");
  CAT_ELE = e.options[e.selectedIndex].value;

  SHOW_ROOTNET = "create";
  var x = document.getElementById("show_rootnet").checked;
  if ( x == true ) {
  } else {
      SHOW_ROOTNET = "";
  }

  SHOW_ENDNET = "create";
  var x = document.getElementById("show_endnet").checked;
  if ( x == true ) {
  } else {
      SHOW_ENDNET = "";
  }

  var COLLAPSE_ROOTNET;
  var x = document.getElementById("hide_not_rooted").checked;
  if ( x == true ) {
      COLLAPSE_ROOTNET = "create";
	  console.log("hide_not_rooted true: " + x);
  } else {
	  console.log("hide_not_rooted false: " + x);
     COLLAPSE_ROOTNET = "";
//      setCookie("HideNotRootedNet", 0, 90)
  }

  e = document.getElementById("entries_per_page");
  ENTRIES_PER_PAGE_ELE = e.options[e.selectedIndex].value;
//  setCookie("EntriesRedPorPage", ENTRIES_PER_PAGE_ELE, 365)

  var SCRIPT;
  var PARAMS_DYN;
  var CLIENT_ID = document.quick_search.client_id.value;
  console.log("CLIENT_ID: " + CLIENT_ID);
  var y = document.getElementById("show_free_ranges").checked;

  if ( y == false ) {
    console.log("SHOW FREE RANGES FALSE: " + y);
    SCRIPT = "index_nohead.cgi";
    PARAMS_DYN="?ip_version_ele=" + IP_VERSION_ELE + "&loc_ele=" + LOC_ELE + "&tipo_ele=" + CAT_ELE + "&show_rootnet=create&show_endnet=" + SHOW_ENDNET + "&hide_not_rooted=" + COLLAPSE_ROOTNET + "&client_id=" + CLIENT_ID + "&parent_network_id=" + id + "&entries_per_page=" + ENTRIES_PER_PAGE_ELE;
  } else {
    console.log("SHOW FREE RANGES TRUE: " + y);
    SCRIPT = "ip_show_free_range_nohead.cgi";
    if ( id ) {
        PARAMS_DYN="?ip_version=" + IP_VERSION_ELE + "&ip_version_ele=" + IP_VERSION_ELE + "&hide_not_rooted=" + COLLAPSE_ROOTNET + "&client_id=" + CLIENT_ID  + "&red_num=" + id + "&rootnet=y" + "&entries_per_page=" + ENTRIES_PER_PAGE_ELE;
    } else {
        PARAMS_DYN="?ip_version=" + IP_VERSION_ELE + "&ip_version_ele=" + IP_VERSION_ELE + "&hide_not_rooted=" + COLLAPSE_ROOTNET + "&client_id=" + CLIENT_ID + "&entries_per_page=" + ENTRIES_PER_PAGE_ELE;
    }
  }


  var URL = "/gestioip/";
  var URL_LOAD = URL + SCRIPT + PARAMS_DYN


  if ( ! NO_RELOAD_TABLE_SET ) {
      console.log("NO_RELOAD_TABLE_SETB: " + NO_RELOAD_TABLE_SET)
      console.log("REFRESH1: " + REFRESH)
      URL_LOAD_ENCODED = encodeURI(URL_LOAD)
      console.log("URL LOAD NO REFRESH: " + URL_LOAD_ENCODED);

      $("#content").load(URL_LOAD_ENCODED);
  }

  if ( NO_RELOAD_TABLE_SET ) {
      NO_RELOAD_TABLE_SET = "";
  }

//  $("#rootnet_tree").jstree("open_all");

});

};
