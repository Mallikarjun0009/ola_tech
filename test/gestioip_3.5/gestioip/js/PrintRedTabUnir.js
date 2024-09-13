function check(boxnr,MESSAGE)
{
var max=2;
var objekte_gewaehlt=0;
for(var i=0; i < document.unirred_form.unirred.length; i++)
if(document.unirred_form.unirred[i].checked==true) objekte_gewaehlt++;
if(objekte_gewaehlt > max)
{
document.unirred_form.unirred[boxnr].checked=false;
alert(MESSAGE);
}
}
