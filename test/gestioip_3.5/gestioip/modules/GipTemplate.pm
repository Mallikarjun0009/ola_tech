### GestioIP template processing
use strict;
package GipTemplate;


sub create_nav_search {
#	my $self = shift;
    my %args = @_;

	my $url=$args{url} || "";
	my $print_site=$args{print_site} || "";
	my $print_line=$args{print_line} || "";

    if ( ! $print_site && ! $print_line ) {
        return "";
    }

	my ($site_search, $line_search);
	$site_search=$line_search="";
	
	my $search = '
       <form class="form-inline" action="$url/{{ SCRIPT }}">
          <input style="height:30px" class="form-control mr-sm-2" type="search" placeholder="{{ SEARCH_TYPE }}" aria-label="networks">
       </form>';

	if ( $print_site ) {
		$site_search = $search;
        $site_search =~ s/\{\{ SCRIPT \}\}/res\/ip_manage_sites.cgi/;
		$site_search =~ s/\{\{ SEARCH_TYPE \}\}/SEARCH SITE/;
	}

	if ( $print_line ) {
        $site_search =~ s/\{\{ SCRIPT \}\}/show_lines.cgi/;
		$line_search = $search;
		$line_search =~ s/\{\{ SEARCH_TYPE \}\}/SEARCH LINE/;
	}

	my $content = '<div class="col-2" style="min-width: 115px;">';
	$content .= $site_search;
	$content .= $line_search;
	$content .= '</div>';

	return $content;
}


sub create_search_field_dropdown_items {
    my %args = @_;

	my $items = $args{items} || "";
    my $item_order = $args{item_order} || "";

	my $content;

    foreach my $name ( @$item_order ) {
        next if $name eq "";
        my $link = "";
        $link = $items->{$name} if exists($items->{$name});
        next if ! $link;

		$content .= '<div class="dropdown-item" href="#" onClick="changePlaceholder(\'' .  $name . '\',\'' . $link . '\')">' . $name . '</div>';
	}

	return $content;
}


sub create_nav_options {
    my %args = @_;

    my $url=$args{url} || "";
    my $print_site=$args{print_site} || "";
	my $items = $args{items} || "";
    my $item_order = $args{item_order} || "";
    my $load_content_only=$args{load_content_only} || "";
    my $link_onclick=$args{link_onclick} || "";
    my $link_style_hash=$args{link_style} || "";
    my $link_title_hash=$args{link_title} || "";

	my $content;

	$content .= '
	<div class="float-right" class="">
        <nav class="navbar navbar-expand-lg navbar-custom-options p-0 m-0" style="height: 20px;">
          <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
          </button>

          <div class="collapse navbar-collapse" id="navbarSupportedContent">
            <ul class="navbar-nav">';


    foreach my $name ( @$item_order ) {
        next if $name eq "";
        my $link = "";
        my $href = "";
        my $onclick = "";
        my $link_style = "";
        my $title = "";
        if ( $link_title_hash ) {
            if ( ref($link_title_hash) eq 'HASH' and exists $link_title_hash->{$name} ) {
    #        $title = $link_title_hash->{$name} if exists($link_title_hash->{$name});
                $title = $link_title_hash->{$name};
            }
        }
        $link = $items->{$name} if exists($items->{$name});
        $onclick = $link_onclick->{$name} if exists($link_onclick->{$name});
        next if ! $link;
        if ( $link ne "NO_LINK" ) {
            $href = 'href="' . $link . '"';
        }
		my $id = $name;
		$id =~ s/\s+/_/g;

        $link_style = "nav-link border-gray-left pr-2 pl-2 pt-0 pb-0 m-0 nowrap";
        if ( $link_style_hash ) {
            if ( $link_style_hash->{$name} ) {
                $link_style = $link_style_hash->{$name} ||  "nav-link border-gray-left pr-2 pl-2 pt-0 pb-0 m-0 nowrap";
                $name = "";
            }
        }

		$content .='
              <li class="nav-item">
               	 <a class="' . $link_style . '" title="' . $title . '" id="' . $id . '" ' . $href . ' ' . $onclick . '>' . $name . '</a>
              </li>';

		if ( exists($load_content_only->{$name}) ) {
			$content .= '
				<script type="text/javascript">

					window.onload = function() {

					  var a = document.getElementById("' . $id . '");
					  a.onclick = function() {
						// disable link and reload content

						$("#content").load("' . $link . '");	

						// do not open a href
						return false;
					  }
					}
				</script>';
		}
	}

	$content .= '
			</ul>
          </div>
		</nav>
	  </div>';

	return $content;
}


sub create_list_view_option_items {
    my %args = @_;

	my $name = $args{name} || "";
    my $onclick = $args{onclick} || "";
    my $disabled = $args{disabled} || "";
    my $nolink = $args{nolink} || "";

    $disabled = "disabled" if $disabled;
    my $link = "";
    $link = 'href="#"' if ! $nolink;
    my $content = '<div class="dropdown-item ' . $disabled . '"' . $link . ' onClick="' . $onclick . '">' . $name . '</div>';

	return $content;
}


sub create_nav_dropdown {
#    my $self = shift;
    my %args = @_;

    my $name = $args{name} || "";
    my $nav_link = $args{nav_link} || "#";
    my $items = $args{items} || "";
    my $item_order = $args{item_order} || "";
    my $target_blank = $args{target_blank} || "";


    my $content = '<li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle nowrap" href="' . $nav_link . '" id="navbarDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">';

    $content .= $name;
    $content .= '</a>';
	$content .= '<div class="dropdown-menu" aria-labelledby="navbarDropdown">';

	my %target_blank = %$target_blank if $target_blank;
	foreach my $item ( @$item_order ) {
        next if $item eq "";
        if ( $item =~ /dropdown-divider/ ) {
            $content .= '<div class="dropdown-divider"></div>';
            next;
        }
        my $link = "";
		my $t_blank = "";
		$t_blank = 'target="_blank"' if exists($target_blank{$item});
		$link = $items->{$item} if exists($items->{$item});
        next if ! $link;

        $content .= '<a class="dropdown-item" href="' . $link . '" '. $t_blank . '>' . $item . '</a>';
	}

	$content .= '</div>';
    $content .= '</li>';

	return $content;
}


sub create_nav_link {
#    my $self = shift;
    my %args = @_;

    my $name=$args{name} || "";
    my $link=$args{link} || "";
    my $glyphicon=$args{glyphicon} || "";

    my $class = "nav-link";
    $class .= " $glyphicon pt-2" if $glyphicon;
    my $content .= '<li class="nav-item">
                 <a class="nav-link nowrap ' . $glyphicon . ' " href="' . $link . '">' . $name . '</a>
                 </li>';

	return $content;
}

sub create_sitebar {
    my %args = @_;

    my $title=$args{title} || "";

# TEST CREATE SITEBAR COLLAPS -> for example in search result 
	my $content ='
    <div class="border-right bg-tree" id="sidebar_container" style="width: 10em;">
        <nav id="sidebar">
            <div class="sidebar-header">
                <h6>' . $title . '</h6>
            </div>

            <div id="rootnet_tree" class="scroll_horizontal"></div>

        </nav>
    </div>

    <div style="width: 12px">
      <div class="btn-gip border mt-2 rounded pointer" id="sidebarCollapse" style="width: 10px; height: 55px;" onclick="check_collapsed_sidebar();">
                <span id="sidebarButtonIcon" class="fa fa-caret-left white" style="margin-top:18px;"></span>
      </div>
    </div>

    <script>
		function check_collapsed_sidebar() {
			if ($("#sidebar").hasClass("active") ) {
				$( "#sidebarButtonIcon" ).removeClass( "fa-caret-right" );
				$( "#sidebarButtonIcon" ).addClass( "fa-caret-left" );
				document.getElementById("sidebar_container").style.width="10em";
                setCookie("CollapseSitebar", "expand", 365);
                load_jstree();
                console.log("Set Cookie CollapseSitebar: expand");
			} else {
				$( "#sidebarButtonIcon" ).removeClass( "fa-caret-left" );
				$( "#sidebarButtonIcon" ).addClass( "fa-caret-right" );
				document.getElementById("sidebar_container").style.width="1px";
                setCookie("CollapseSitebar", "collapse", 365);
                console.log("Set Cookie CollapseSitebar: collapse");
			}
		}

		function collapse_expand_sidebar() {
            var VALUE = getCookie("CollapseSitebar");
            console.log("CollapseSitebar: " + VALUE)
			if ( VALUE == "collapse" ) {
                $("#sidebar").toggleClass("active");
				$( "#sidebarButtonIcon" ).removeClass( "fa-caret-right" );
				$( "#sidebarButtonIcon" ).addClass( "fa-caret-left" );
				document.getElementById("sidebar_container").style.width="1px";
                console.log("collapsing sitebar");
			} else {
				document.getElementById("sidebar_container").style.width="10em";
            }
		}
    </script>

    <script type="text/javascript">
        $(document).ready(function () {
            $("#sidebarCollapse").on("click", function () {
                $("#sidebar").toggleClass("active");
            });
            collapse_expand_sidebar();
        });
    </script>';

	return $content;
}

sub create_div_inhalt {
    my %args = @_;

    my $noti=$args{noti} || "";
    
	my $content;
    $content .= '<div id="Inhalt" class="w-100">';
	$content .= '<div class="alert Notify_bg alert-dismissible fade show" role="alert" id="NotifyText">' . $noti . '
		  <button type="button" class="close" data-dismiss="alert" aria-label="Close">
			<span aria-hidden="true">&times;</span>
		  </button>
		</div>' if $noti;

	return $content;
}

sub create_div_notify_text {
    my %args = @_;

    my $noti=$args{noti} || "";
    
	my $content;
	$content .= '<div class="alert Notify_bg alert-dismissible fade show" role="alert" id="NotifyText">' . $noti . '
		  <button type="button" class="close" data-dismiss="alert" aria-label="Close">
			<span aria-hidden="true">&times;</span>
		  </button>
		</div>' if $noti;

	return $content;
}

sub create_red_head_inline_form {
    my %args = @_;

    my $id=$args{form_id} || "";
    my $link=$args{link} || "";
    my $form_elements=$args{form_elements} || "";
    my $method=$args{method} || "";
    my $pages_links=$args{pages_links} || "";
    my $fav_button=$args{fav_button} || "";

	$method = 'method="' . $method . '"' if $method;

    my $content = "";

#    $content .= '<div id="quick_filter_networks" class="container-fluid w-100">';
#    $content .= '<form class="form-inline" action="' . $link . '" id="' . $id . '" name="' . $id . '"' . $method . '>';
#    $content .= $form_elements;
#    $content .= "</form></div>";

    $content .= '<div id="quick_filter_networks" class="container-fluid w-100">';
    $content .= '<div class="row">';
#    $content .= '<div class="col-10">';
    $content .= '<div class="col-9">';
    $content .= '<form class="form-inline" action="' . $link . '" id="' . $id . '" name="' . $id . '"' . $method . '>';
    $content .= $form_elements;
    $content .= "</form>";
    $content .= '</div>';
    $content .= '<div class="col-2">';
    $content .= '<div id="pages_links_net">';
    $content .= $pages_links;
    $content .= '</div>';
    $content .= '</div>';
    $content .= '<div class="col-1">';
    $content .= $fav_button;
    $content .= '</div>';
    $content .= '</div>';
    $content .= '</div>';
    

	return $content;
}


sub create_form_reset_button {
    my %args = @_;

    my $text=$args{text} || "";
    my $onclick=$args{onclick} || "";

    my $content;

#    $content .= '<div class="font-weight-bold color-link pointer" ' . $onclick . '>' . $text . '</div>';
    $content .= '<div class="btn pointer m-0 p-0" ' . $onclick . '>' . $text . '</div>';

    return $content;
}

sub create_form {
    my %args = @_;

    my $id=$args{form_id} || "";
    my $link=$args{link} || "";
    my $form_elements=$args{form_elements} || "";
    my $method=$args{method} || "";
    my $class=$args{class} || "form-horizontal";
    my $autocomplete=$args{autocomplete} || "on";


	$method = 'method="' . $method . '"' if $method;
    if ( $autocomplete eq "off" ) {
        $autocomplete = 'autocomplete="off"';
    } else {
        $autocomplete = "";
    }

    my $content = '<div class="container-fluid p-3">';
    $content .= '<form class="' . $class . '" action="' . $link . '" id="' . $id . '" name="' . $id . '" ' . $method . ' ' . $autocomplete . '>';
    $content .= $form_elements;
    $content .= "</form></div>";

	return $content;
}

sub create_form_element_hidden {
    my %args = @_;

    my $name=$args{name} || "";
    my $value=$args{value} || "";
    my $id = $name;

    my $element = '<input type="hidden" name="' . $name . '" id="' . $id . '" value="' . $value . '">';

    return $element;
}


sub create_form_element_choice_radio {
    my %args = @_;

    my $id=$args{id} || "";
    my $value1=$args{value1} || "";
    my $value2=$args{value2} || "";
    my $value3=$args{value3} || "";
    my $checked1=$args{checked1} || "";
    my $checked2=$args{checked2} || "";
    my $checked3=$args{checked3} || "";
    my $text1=$args{text1} || "";
    my $text2=$args{text2} || "";
    my $text3=$args{text3} || "";
    my $label=$args{label} || "";
    my $margin_top=$args{margin_top} || "";
    my $margin_bottom=$args{margin_bottom} || "";
    my $required=$args{required} || "";
    my $hint_text=$args{hint_text} || "";
    my $hint_text_span_id=$args{hint_text_span_id} || "";
    my $onclick=$args{onclick} || "";
    my $disabled = $args{disabled} || "";


    $checked1 = "checked" if $checked1;
    $checked2 = "checked" if $checked2;
    $checked3 = "checked" if $checked3;
    $required = "required" if $required;
    $disabled = "disabled" if $disabled;

    my $element;
	$element .= '<div class="form-group row ' . $margin_top . ' ' . $margin_bottom . ' ' . $required . '">';
	$element .= '<label for="' . $id . '" class="col-sm-1 control-label">' . $label . '</label>';
	$element .= '<div class="col-sm-6">';

    $element .= $text1 . ' <input type="radio" class="mr-3" name="' . $id . '" id="' . $id . '" value="' . $value1 . '" ' . $checked1 . ' ' . $onclick . ' ' . $disabled . '>';
    $element .= $text2 . ' <input type="radio" class="mr-3" name="' . $id . '" id="' . $id . '" value="' . $value2 . '" ' . $checked2 . ' ' . $onclick . ' ' . $disabled . '>';
    $element .= $text3 . ' <input type="radio" name="' . $id . '" id="' . $id . '" value="' . $value3 . '" ' . $checked3 . ' ' . $onclick . ' ' . $disabled . '>' if $text3;

	if ( $hint_text ) {
		$element .= '<span id="' . $hint_text_span_id . '" class="pl-2 display-inline">' . $hint_text . '</span>';
	}

	$element .= '</div>';
	$element .= '</div>';

    return $element;
}


sub create_form_element_color {
    my %args = @_;

    my $id=$args{id} || "";
    my $value=$args{value} || "";
    my $label=$args{label} || "";
    my $width=$args{width} || "180";
    my $maxlength=$args{maxlength} || "100";
    my $size=$args{size} || "10";
    my $required=$args{required} || "";
    my $hint_text=$args{hint_text} || "";
    my $hint_text_span_id=$args{hint_text_span_id} || "";
    my $print_calc_link=$args{print_calc_link} || "";
    my $before_text_span_id=$args{before_text_span_id} || "";
    my $before_text=$args{before_text} || "";
    my $disabled=$args{disabled} || "";

    my $calc_link = "";
    $calc_link = '<span class="pl-2 btn pointer display-inline" onClick="calculate_different_BM();">' . $print_calc_link . '</span>' if $print_calc_link;
    $maxlength = 'maxlength="' . $maxlength . '"' if $maxlength;
    $size = 'size="' . $size . '"' if $size;
# TEST change px to em
    my $style = 'style="width: ' . $width . 'em"' if $width;
    $required = "required" if $required;

    my $element;
    $element .= '<div class="form-group row ' . $required . '">';
    $element .= '<label for="' . $id . '" class="col-sm-1 control-label">' . $label . '</label>';
    $element .= '<div class="col-sm-5">';
#    if ( $before_text ) {
#        $element .= '<span class="pr-1" id="' . $before_text_span_id . '" class="pl-2 display-inline">' . $before_text . '</span>';
#    }
    $element .= '<input class="form-control form-control-sm display-inline" ' . $style . ' type="color" id="' . $id . '" name="' . $id . '" value="' . $value . '" ' . $maxlength . ' ' . $size . ' ' . $required . ' ' . $disabled . '>';
#    if ( $hint_text ) {
#        $element .= '<span id="' . $hint_text_span_id . '" class="pl-2 display-inline">' . $hint_text . '</span>' . $calc_link;
#    }
    $element .= '</div>';
    $element .= '</div>';

    return $element;
}


sub create_form_element_text {
    my %args = @_;

    my $id=$args{id} || "";
    my $value=$args{value} || "";
    my $label=$args{label} || "";
    my $width=$args{width} || "180";
    my $maxlength=$args{maxlength} || "100";
    my $size=$args{size} || "10";
    my $required=$args{required} || "";
    my $hint_text=$args{hint_text} || "";
    my $hint_text_span_id=$args{hint_text_span_id} || "";
	my $print_calc_link=$args{print_calc_link} || "";
	my $before_text_span_id=$args{before_text_span_id} || "";
	my $before_text=$args{before_text} || "";
	my $disabled=$args{disabled} || "";
    my $display=$args{display} || "";
    my $margin_top=$args{margin_top} || "";
    my $margin_bottom=$args{margin_bottom} || "";
    my $type=$args{type} || "text";
	my $readonly=$args{readonly} || "";
	my $col_sm=$args{col_sm} || "col-sm-6";

    $disabled = "disabled" if $disabled;
    $readonly = "readonly" if $readonly;
	$margin_top = "mt-" . $margin_top if $margin_top;
    $margin_bottom = "mb-" . $margin_bottom if $margin_bottom;
    $required = "required" if $required;

	my $calc_link = "";
	$calc_link = '<span class="pl-2 btn pointer display-inline" onClick="calculate_different_BM();">' . $print_calc_link . '</span>' if $print_calc_link;
	$maxlength = 'maxlength="' . $maxlength . '"' if $maxlength;
	$size = 'size="' . $size . '"' if $size;
# TEST change px to em
	my $style = 'style="width: ' . $width . 'px"' if $width;

    my $element;
	$element .= '<div class="form-group row ' . $margin_top . ' ' . $margin_bottom . ' ' . $required . '">';
	$element .= '<label for="' . $id . '" class="col-sm-1 control-label">' . $label . '</label>';
	$element .= '<div class="' . $col_sm . '">';
	if ( $before_text ) {
        $element .= '<span class="p-2 display-inline" id="' . $before_text_span_id . '" style=" ' . $display . '">' . $before_text . '</span>';
	}
	$element .= '<input class="form-control form-control-sm form-control-inline" ' . $style . ' type="' . $type . '" id="' . $id . '" name="' . $id . '" value="' . $value . '" ' . $maxlength . ' ' . $size . ' ' . $required . ' ' . $disabled . ' ' . $readonly . '>';
	if ( $hint_text ) {
		$element .= '<span id="' . $hint_text_span_id . '" class="pl-2 display-inline">' . $hint_text . '</span>' . $calc_link;
	}
	$element .= '</div>';
	$element .= '</div>';

    return $element;
}

sub create_form_element_select_filter {
    my %args = @_;

    my $name=$args{name} || "";
    my $label=$args{label} || "";
    my $items=$args{items} || "";
    my $item_order=$args{item_order} || "";
    my $id=$args{id} || "";
    my $placeholder=$args{placeholder} || "";
    my $onclick=$args{onclick} || "";
    my $selected_value=$args{selected_value} || "";
    my $width=$args{width} || "";

	$name = $label if $label;

    my $content;
    my $empty = "";
    if ( $placeholder ) {
        $empty = "empty";
    }
	$content .= '<label for="' . $id . '">' . $name . '</label>';
#	$content .= '<select class="form-control form-control-sm m-2 placeholder custom-select" style="width: ' . $width . '; height: 28px; font-size: 13px;" id="' . $id . '" name="' . $id . '" ' . $onclick . '>';
	$content .= '<select class="m-2 custom-select ' . $empty . '" style="width: ' . $width . '; height: 30px; font-size: 12px;" id="' . $id . '" name="' . $id . '" ' . $onclick . '>';
    $content .= '<option value="" selected="selected">' . $placeholder . '</option>' if $placeholder;

    my $selected = "";
	foreach my $item ( @$item_order ) {
        my $value = "";
        if ( $items ) {
            $value = $items->{$item} if exists($items->{$item});
        } else {
            $value = $item;
        }
        next if ! $value;

        $selected = "selected" if $value eq $selected_value;
		$content .= '<option value="' . $value . '" ' . $selected . '>' . $item . '</option>';
        $selected = "";
	}

	$content .= '</select>';

    return $content;
}


sub create_form_element_select {
    my %args = @_;

    my $name=$args{name} || "";
    my $label=$args{label} || "";
    my $items=$args{items} || "";
    my $item_order=$args{item_order} || "";
    my $id=$args{id} || "";
    my $onclick=$args{onclick} || "";
    my $selected_value=$args{selected_value} || "";
    my $width=$args{width} || "";
    my $required=$args{required} || "";
    my $multiple=$args{multiple} || "";
    my $size=$args{size} || "1";
    my $first_no_option=$args{first_no_option} || "";
    my $no_label=$args{no_label} || "";
    my $pm=$args{pm} || "";
    my $disabled_options=$args{disabled_options} || "";
    my $hint_text=$args{hint_text} || "";
    my $hint_text_span_id=$args{hint_text_span_id} || "";
    my $hint_text_onclick=$args{hint_text_onclick} || "";
    my $hint_text_class=$args{hint_text_class} || "";
    my $before_text_span_id=$args{before_text_span_id} || "";
    my $before_text=$args{before_text} || "";
    my $option_style=$args{option_style} || "";
	my $disabled=$args{disabled} || "";
	my $without_search=$args{without_search} || "";
    my $no_row_start=$args{no_row_start} || "";
    my $no_row_end=$args{no_row_end} || "";
    my $display=$args{display} || "";
#    my $over_text=$args{over_text} || "";
    my $margin_top=$args{margin_top} || "";
    my $margin_bottom=$args{margin_bottom} || "";
    my $readonly=$args{readonly} || "";

	$name = $label if $label;
    $disabled = "disabled" if $disabled;
    $readonly = "readonly" if $readonly;
    $margin_top = "mt-" . $margin_top if $margin_top;
    $margin_bottom = "mb-" . $margin_bottom if $margin_bottom;

	$size = 'size="' . $size . '"';
    $multiple = "multiple" if $multiple;
    $display = 'display: none;"' if $display eq "none";
    $required = "required" if $required;

	my $empty_selected = "";
	if ( ! $selected_value && $selected_value ne "0" ) {
		$empty_selected = 1;
	}
    my $content;
    $content .= '<div class="form-group row ' . $margin_top . ' ' . $margin_bottom . ' ' . $required . '">' if ! $no_row_start;
    $content .= '<label class="control-label col-sm-1" for="' . $id . '" >' . $name . '</label>' if ! $no_label;
    $content .= '<div class="col-sm-10">'  if ! $no_row_start;
#    $content .= "$over_text<br>" if $over_text;
	if ( $before_text ) {
        $content .= '<span class="pr-1 pl-2 display-inline" id="' . $before_text_span_id . '" style=" ' . $display . '">' . $before_text . '</span>';
    }

    $content .= '<select class="custom-select custom-select-sm display-inline ' . $pm . '" style="width: ' . $width . '; ' . $display . '" id="' . $id . '" name="' . $id . '" ' . $size . ' ' . $onclick . ' ' . $required . ' ' . $multiple . ' ' . $disabled . ' ' . $readonly . '>';
    $content .= '<option value=""></option>' if $first_no_option;

    my $selected = ""; 
    foreach my $item ( @$item_order ) {
		my $disabled = ""; 
        my $value = "";
        if ( $items ) {
            $value = $items->{$item} if exists($items->{$item});
        } else {
            $value = $item;
        }

		if ( $disabled_options ) {
			$disabled = "disabled" if exists $disabled_options->{$item};
		}


        
        if ( $selected_value =~ /^\Q$value\E\|/ || $selected_value =~ /\|\Q$value\E\|/ || $selected_value =~ /\|\Q${value}\E$/ ) {
                $selected = "selected";
        } else {
            if ( $value eq $selected_value ) {
                $selected = "selected";
            }
            if ( $value eq "" && $empty_selected ) {
                $selected = "selected";
            }
            if ( $value eq "0" && $selected_value eq "NULL_VALUE") {
                $selected = "selected";
            }
        }

        if ( $item eq "EMPTY_OPTION" ) {
			$value = $item = "";
        } elsif ( $item eq "M1_OPTION" ) {
			$item = "";
			$value = "-1";
		}

		my $style = "";
		if ( $option_style ) {
			if ( defined ($option_style->{$item})) {
				$style = $option_style->{$item};
			}
		}

        $content .= '<option ' . $style . ' value="' . $value . '" ' . $selected . ' ' . $disabled . '>' . $item . '</option>';
        $selected = "";
    }

    if ( $without_search ) {
        $content .= '<option value="NULL">' . $without_search . '</option>';
    }

    $content .= '</select>';
	if ( $hint_text ) {
		$content .= '<span id="' . $hint_text_span_id . '" class="p-2 display-inline' . $hint_text_class . '" ' . $hint_text_onclick . ' style=" ' . $display . '">' . $hint_text . '</span>';
	}
    $content .= '</div>' if ! $no_row_end;
    $content .= '</div>' if ! $no_row_end;

    return $content;
}



sub create_form_element_checkbox {
    my %args = @_;

    my $label=$args{label} || "";
    my $label_bold=$args{label_bold} || "";
    my $label_id=$args{label_id} || "";
    my $value=$args{value} || "";
    my $id=$args{id} || "";
    my $checked=$args{checked} || "";
    my $onclick=$args{onclick} || "";
    my $disabled=$args{disabled} || "";
    my $hint_text=$args{hint_text} || "";
    my $hint_text_span_id=$args{hint_text_span_id} || "";
    my $required=$args{required} || "";
    my $readonly=$args{readonly} || "";

    my $content;
	$checked = "checked" if $checked;
	$disabled = "disabled" if $disabled;
	$label_id = 'id="' . $label_id . '"';
    $label_bold = "font-weight-bold" if $label_bold;
	my $hint_id = 'id="' . $id . '_hint_text"';
    $required = "required" if $required;
#    $readonly = "readonly" if $readonly;
    $readonly = "onclick='return false;'" if $readonly;

	$content .= '
  <div class="form-group row  ' . $required . '">
    <div class="col-sm-1 ' . $label_bold . '" ' . $label_id . '>' . $label . '</div>
    <div class="col-sm-5">
      <div class="form-check">
		<label class="custom-control custom-checkbox required">
		<input type="checkbox" class="custom-control-input" value="' . $value . '" id="' . $id . '" name="' . $id . '" ' . $onclick . ' ' . $checked . ' ' . $disabled . ' ' . $required . ' ' . $readonly . '>
		  <span class="custom-control-label pr-2" ' . $hint_id . '>' . $hint_text . '</span>
        </label>';
#    if ( $hint_text ) {
#        $content .= '<span id="' . $hint_text_span_id . '" class="pl-2 display-inline">' . $hint_text . '</span>';
#    }
     $content .= '</div>
    </div>
    </div>';

    return $content;
}



sub create_form_element_radio_inline_ip_version {
    my %args = @_;

    my $label=$args{label} || "";
    my $disabled_ipv4=$args{disabled_ipv4} || "";
    my $disabled_ipv6=$args{disabled_ipv6} || "";
    my $checked_ipv4=$args{checked_ipv4} || "";
    my $checked_ipv6=$args{checked_ipv6} || "";

	$disabled_ipv4 = "disabled" if $disabled_ipv4;
	$disabled_ipv6 = "disabled" if $disabled_ipv6;
	$checked_ipv4 = "checked" if $checked_ipv4;
	$checked_ipv6 = "checked" if $checked_ipv6;

	my $onclick_v4 = 'onchange="change_BM_select(\'v4\',\'networks /64\');"';
	my $onclick_v6 = 'onchange="change_BM_select(\'v6\',\'networks /64\');"';

	my $content;

    $content .= '
  <div class="form-group row">
    <div class="col-sm-1">' . $label . '</div>
    <div class="col-sm-10">';

    $content .= '
    <div class="custom-control custom-control-inline">
        <label class="custom-control custom-radio">
        <input type="radio" class="custom-control-input custom-control-inline" value="v4" id="ip_version" name="ip_version" ' . $onclick_v4 . ' ' . $disabled_ipv4 . ' ' . $checked_ipv4 . '>
          <span class="custom-control-label pr-2">IPv4</span>
        </label>
     </div>';

    $content .= '
    <div class="custom-control custom-control-inline">
        <label class="custom-control custom-radio">
        <input type="radio" class="custom-control-input custom-control-inline" value="v6" id="ip_version" name="ip_version" ' . $onclick_v6 . ' ' . $disabled_ipv6 . ' ' . $checked_ipv6 . '>
          <span class="custom-control-label pr-2">IPv6</span>
        </label>
     </div>';

    $content .= '</div></div>';

    return $content;
}


sub create_form_element_checkbox_filter {
    my %args = @_;

    my $label=$args{label} || "";
    my $value=$args{value} || "";
    my $id=$args{id} || "";
    my $checked=$args{checked} || "";
    my $onclick=$args{onclick} || "";
    my $disabled=$args{disabled} || "";
    my $autocomplete_off=$args{autocomplete_off} || "";

    my $content;
	$checked = "checked" if $checked;
	$disabled = "disabled" if $disabled;
	$autocomplete_off = 'autocomplete="off"' if $autocomplete_off;

    $content .= '
	<div class="form-check">
	<label class="custom-control custom-checkbox">
		  <input type="checkbox" class="custom-control-input pl-2" value="' . $value . '" id="' . $id . '" name="' . $id . '" ' . $onclick . ' ' . $checked . ' ' . $disabled . ' ' . $autocomplete_off .'>
		  <span class="custom-control-label pr-2">' . $label . '</span>
	</label>
	</div>'; 

    return $content;
}


sub create_form_element_comment {
    my %args = @_;

    my $comment=$args{comment} || "";
    my $value=$args{value} || "";
    my $id=$args{id} || "";
    my $label=$args{label} || "";
    my $onclick=$args{onclick} || "";
    my $class=$args{class} || "";

    $comment = $value if $value && ! $comment;

    my $content;

	$content .= '<div class="form-group row">';
	$content .= '<label class="control-label col-sm-1" for="' . $id . '">' . $label . '</label>';
    $content .= '<div class="col-sm-10">';
    $content .= '<input type="text" readonly class="form-control-plaintext '. $class .'" id="' . $id . '" value="' . $comment . '" ' . $onclick . '>';
#    $content .= '<div id="' . $id . '">' . $comment . '</div>';
	$content .= '</div>';
	$content .= '</div>';

    return $content;
}


sub create_form_element_button {
    my %args = @_;

    my $value=$args{value} || "";
    my $id=$args{id} || "";
    my $name=$args{name} || "";
    my $onclick=$args{onclick} || "";
    my $class_args=$args{class_args} || "";
    my $disabled=$args{disabled} || "";
    $id = $name if $name && ! $id;

	$disabled = "disabled" if $disabled;

	my $content;

    $content .= '<div class="form-group row">';
    $content .= '<div class="col-sm-10">';
    $content .= '  <button type="submit" class="btn ' . $class_args . '" id="' . $id . '" name="' . $id . '" ' . $onclick . ' ' . $disabled . '>' . $value . '</button>';
    $content .= '</div>';
    $content .= '</div>';

    return $content;
}

sub create_form_element_link {
    my %args = @_;

    my $value=$args{value} || "";
    my $id=$args{id} || "";
    my $onclick=$args{onclick} || "";
    my $class_args=$args{class_args} || "";

	my $content;

    $content .= '<div class="form-group row">';
    $content .= '<div class="col-sm-10 pt-4">';
    $content .= '  <span type="button" class="btn ' . $class_args . '" id="' . $id . '" name="' . $id . '" ' . $onclick . '>' . $value . '</span>';
    $content .= '</div>';
    $content .= '</div>';

    return $content;
}

sub create_form_element_link_form {
    my %args = @_;

    my $label=$args{label} || "";
    my $value=$args{value} || "";
    my $id=$args{id} || "";
    my $onclick=$args{onclick} || "";
    my $class_args=$args{class_args} || "";

	my $content;

    $content .= '<div class="form-group row">';
	$content .= '<label for="' . $id . '" class="col-sm-1 control-label">' . $label . '</label>';
    $content .= '<div class="col-sm-10">';
    $content .= '  <span type="button" class="btn bt-sm p-0 m-0' . $class_args . '" id="' . $id . '" name="' . $id . '" ' . $onclick . '>' . $value . '</span>';
    $content .= '</div>';
    $content .= '</div>';

    return $content;
}

sub create_form_element_textarea {
    my %args = @_;

    my $id=$args{id} || "";
    my $value=$args{value} || "";
    my $label=$args{label} || "";
    my $maxlength=$args{maxlength} || "100";
    my $rows=$args{rows} || "3";
    my $cols=$args{cols} || "50";
    my $wrap=$args{wrap} || "physical";
    my $required=$args{required} || "";

	$maxlength = 'maxlength="' . $maxlength . '"';
    $rows = 'rows="' . $rows . '"';
    $cols = 'cols="' . $cols . '"';
    $wrap = 'wrap="' . $wrap . '"';
    $required = "required" if $required;

    my $element;
	$element .= '<div class="form-group row ' . $required . '">';
	$element .= '<label for="' . $id . '" class="col-sm-1 control-label">' . $label . '</label>';
	$element .= '<div class="col-sm-10">';
	$element .= '<textarea class="form-control form-control-sm" id="' . $id . '" name="' . $id . '" ' . $maxlength . ' ' . $rows . ' ' . $cols . ' ' . $wrap . ' ' . $required . '>';
    $element .= $value;
	$element .= '</textarea>';
	$element .= '</div>';
	$element .= '</div>';

    return $element;
}

sub create_form_element_datetimepicker {
    my %args = @_;

    my $id=$args{id} || "";
    my $value=$args{value} || "";
    my $label=$args{label} || "";

    my $content;
    $content .= '<div class="form-group row">';
    $content .= '<label for="' . $id . '" class="col-sm-1 control-label">' . $label . '</label>';
    $content .= '<div class="col-sm-4">';
    $content .= '<div class="input-group date" id="' . $id . '">';
    $content .= '<input type="text" class="form-control form-control-sm display-inline datepick" size="10" style="width: 180px" />';
    $content .= '<span class="input-group-addon">';
    $content .= '<span class="fa fa-calendar"></span>';
    $content .= '</span>';
    $content .= '</div>';
    $content .= '</div>';
    $content .= '</div>';

	$content .= '
        <script type="text/javascript">
            $(function () {
                $("#' . $id . '").datetimepicker();
            });
        </script>
	';

    return $content;
}

sub create_focus_js {
    my %args = @_;

    my $form=$args{form} || "";
    my $field=$args{field} || "";

	my $content;

	$content .= '<script type="text/javascript">
    			document.' . $form . '.' . $field . '.focus();
				</script>';

	return $content;
}



1;
