#!/usr/bin/perl -T -w


# Copyright (C) 2019 Marc Uebel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


use strict;
use lib '../modules';
use GestioIP;

#my $gip = GestioIP -> new();
#
#my $first_client_id = $gip->get_first_client_id() || 1;
#my $client_id = $gip->get_default_client_id("$first_client_id");
#
#my $user=$ENV{'REMOTE_USER'};
#$gip->delete_user_csrf_token("$client_id", "$user");

print_html();

sub print_html {

print <<EOF;
Content-type: text/html\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
"http://www.w3.org/TR/html4/loose.dtd">
<HTML>
<head><title>GestioIP logout</title>
<script type="text/javascript">
var seconds = 3;
var url="..";

function redirect(){
if (seconds <= 0){
// redirect to new url after counter down.
window.location = url;
}else{
seconds--;
document.getElementById("pageInfo").innerHTML = "redirect in "+seconds+" seconds to the <a href='..'>login page</a>."
setTimeout("redirect()", 1000)
}
}


function backButtonOverride()
{
    setTimeout("backButtonOverrideBody()", 1);
}

function backButtonOverrideBody()
{
    // Works if we backed up to get here
    try
    {
        window.history.forward(1);
    } 
    catch (e)
    {
        // OK to ignore
    }
    // Every quarter-second, try again. The only
    // guaranteed method for Opera, Firefox,
    // and Safari, which don't always call
    // onLoad but *do* resume any timers when
    // returning to a page
    setTimeout("backButtonOverrideBody()", 1000);
}

if (window.addEventListener) // W3C standard
{
    window.addEventListener('load', backButtonOverride, false); // NB **not** 'onload'
}
else if (window.attachEvent) // Microsoft
{
    window.attachEvent('onload', backButtonOverride);
}
</script>

<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<link rel="shortcut icon" href="/favicon.ico">
</head>

<body>
<center>
<p></p>
<br>
<p></p>
<br>
<h2>You have signed out from Gesti&oacute;IP</h2>
<p></p>
<p></p>
<div id="pageInfo">
<script>
redirect();
</script>

</div>
</center>

</body>
</html>
EOF
}
