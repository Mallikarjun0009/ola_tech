#!/usr/bin/perl -T -w


# Copyright (C) 2011 Marc Uebel

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
use DBI;
use lib './modules';
use GestioIP;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");


# Parameter check
my $lang = $daten{'lang'} || "";
$lang="" if $lang !~ /^\w{1,3}$/;
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
) || "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{ip_info_message}","$vars_file");


print <<EOF;

<div class="container">
<br>
<h4>Reserved IPv4 Address blocks</h4>
<br>
<table class="table">
  <thead>
    <tr>
      <th scope="col">Address Block</th>
      <th scope="col">Host range</th>
      <th scope="col">NAME</th>
      <th scope="col">RFCs</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>10.0.0.0/8</td>
      <td>10.0.0.1 - 10.255.255.254</td>
      <td>Private use</td>
      <td><a href="https://www.iana.org/go/rfc1918" target="_blank">[RFC1918]</a></td>
    </tr>
    <tr>
      <td>127.0.0.0/8</td>
      <td>127.0.0.1 - 127.255.255.254</td>
      <td>Loopback</td>
      <td><a href="https://www.iana.org/go/rfc1122#section-3.2.1.3" target="_blank">[RFC1122]</a>, Section 3.2.1.3</td>
    </tr>
    <tr>
      <td>169.254.0.0/16</td>
      <td>169.254.0.1 - 169.254.255.254</td>
      <td>Link Local</td>
      <td><a href="https://www.iana.org/go/rfc3927" target="_blank">[RFC3927]</a></td>
    </tr>
    <tr>
      <td>172.16.0.0/12</td>
      <td>172.16.0.1 - 172.31.255.254</td>
      <td>Private use</td>
      <td><a href="https://www.iana.org/go/rfc1918" target="_blank">[RFC1918]</a></td>
    </tr>
    <tr>
      <td>192.168.0.0/24</td>
      <td>192.168.0.1 - 192.168.255.254 </td>
      <td>Private use</td>
      <td><a href="https://www.iana.org/go/rfc1918" target="_blank">[RFC1918]</a></td>
    </tr>
  </tbody>
</table>
<p>
Visit the <a href="https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml" target="_blank">"IANA IPv4 Special-Purpose Address Registry"</a> for a complete list of reserved IPv4 Address blocks.
<br>
<p>
<br>
<h4>List of variable IPv4 subnet lengths</h4>
<br>
<table class="table table-striped table-hover">
  <thead>
    <tr>
      <th scope="col">Bitmask (CIDR)</th>
      <th scope="col">Subnet mask</th>
      <th scope="col">Number of addresses</th>
      <th scope="col">Number of classful networks</th>
    </tr>
  </thead>
  <tbody>
	<tr><td> /1</td><td>128.0.0.0</td><td>2048 M</td><td>128 A</td></tr>
	<tr><td> /2</td><td>192.0.0.0</td><td>1024 M</td><td>64 A</td></tr>
	<tr><td> /3</td><td>224.0.0.0</td><td>512 M</td><td>32 A</td></tr>
	<tr><td> /4</td><td>240.0.0.0</td><td>256 M</td><td>16 A</td></tr>
	<tr><td> /5</td><td>248.0.0.0</td><td>128 M</td><td>8 A</td></tr>
	<tr><td> /6</td><td>252.0.0.0</td><td>64 M</td><td>4 A</td></tr>
	<tr><td> /7</td><td>254.0.0.0</td><td>32 M</td><td>2 A</td></tr>
	<tr><td> /8</td><td>255.0.0.0</td><td>16 M</td><td>1 A</td></tr>
	<tr><td class="table-secondary" colspan=4 height="10px"></td><tr>
	<tr><td> /9</td><td>255.128.0.0</td><td>8 M</td><td>128 B</td></tr>
	<tr><td>/10</td><td>255.192.0.0</td><td>4 M</td><td>64 B</td></tr>
	<tr><td>/11</td><td>255.224.0.0</td><td>2 M</td><td>32 B</td></tr>
	<tr><td>/12</td><td>255.240.0.0</td><td>1024 K</td><td>16 B</td></tr>
	<tr><td>/13</td><td>255.248.0.0</td><td>512 K</td><td>8 B</td></tr>
	<tr><td>/14</td><td>255.252.0.0</td><td>256 K</td><td>4 B</td></tr>
	<tr><td>/15</td><td>255.254.0.0</td><td>128 K</td><td>2 B</td></tr>
	<tr><td>/16</td><td>255.255.0.0</td><td>64 K</td><td>1 B</td></tr>
	<tr><td class="table-secondary" colspan=4 height="10px"></td><tr>
	<tr><td>/17</td><td>255.255.128.0</td><td>32 K</td><td>128 C</td></tr>
	<tr><td>/18</td><td>255.255.192.0</td><td>16 K</td><td>64 C</td></tr>
	<tr><td>/19</td><td>255.255.224.0</td><td>8 K</td><td>32 C</td></tr>
	<tr><td>/20</td><td>255.255.240.0</td><td>4 K</td><td>16 C</td></tr>
	<tr><td>/21</td><td>255.255.248.0</td><td>2 K</td><td>8 C</td></tr>
	<tr><td>/22</td><td>255.255.252.0</td><td>1 K</td><td>4 C</td></tr>
	<tr><td>/23</td><td>255.255.254.0</td><td>512</td><td>2 C</td></tr>
	<tr><td class="table-secondary" colspan=4 height="10px"></td><tr>
	<tr><td>/24</td><td>255.255.255.0</td><td>256</td><td>1 C</td></tr>
	<tr><td>/25</td><td>255.255.255.128</td><td>128</td><td>&frac12; C</td></tr>
	<tr><td>/26</td><td>255.255.255.192</td><td>64</td><td>&frac14; C</td></tr>
	<tr><td>/27</td><td>255.255.255.224</td><td>32</td><td>&frac18; C</td></tr>
	<tr><td>/28</td><td>255.255.255.240</td><td>16</td><td><sup>1</sup>&frasl;<sub>16</sub> C</td></tr>
	<tr><td>/29</td><td>255.255.255.248</td><td>8</td><td><sup>1</sup>&frasl;<sub>32</sub> C</td></tr>
	<tr><td>/30</td><td>255.255.255.252</td><td>4</td><td><sup>1</sup>&frasl;<sub>64</sub> C</td></tr>
	<tr><td>/31</td><td>255.255.255.254</td><td>2</td><td><sup>1</sup>&frasl;<sub>128</sub> C</td></tr>
	<tr><td>/32</td><td>255.255.255.255</td><td>1</td><td>single host route</td></tr>
  </tbody>
</table>
<div class="float-right">(M=10<sup>6</sup>, K=10<sup>3</sup>)</div>
See also <a href="https://www.ietf.org/rfc/rfc1878.txt" target="_blank">RFC 1878</a>

</div>

EOF
$gip->print_end("$client_id","$vars_file","", "$daten");
