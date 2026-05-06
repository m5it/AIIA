<?php require_once('../Connections/sanmig.php'); ?>
<?php
if (!function_exists("GetSQLValueString")) {
function GetSQLValueString($theValue, $theType, $theDefinedValue = "", $theNotDefinedValue = "") 
{
  $theValue = get_magic_quotes_gpc() ? stripslashes($theValue) : $theValue;

  $theValue = function_exists("mysql_real_escape_string") ? mysql_real_escape_string($theValue) : mysql_escape_string($theValue);

  switch ($theType) {
    case "text":
      $theValue = ($theValue != "") ? "'" . $theValue . "'" : "NULL";
      break;    
    case "long":
    case "int":
      $theValue = ($theValue != "") ? intval($theValue) : "NULL";
      break;
    case "double":
      $theValue = ($theValue != "") ? "'" . doubleval($theValue) . "'" : "NULL";
      break;
    case "date":
      $theValue = ($theValue != "") ? "'" . $theValue . "'" : "NULL";
      break;
    case "defined":
      $theValue = ($theValue != "") ? $theDefinedValue : $theNotDefinedValue;
      break;
  }
  return $theValue;
}
}

$editFormAction = $_SERVER['PHP_SELF'];
if (isset($_SERVER['QUERY_STRING'])) {
  $editFormAction .= "?" . htmlentities($_SERVER['QUERY_STRING']);
}

if ((isset($_POST["MM_insert"])) && ($_POST["MM_insert"] == "form1")) {
  # Update time to 24 hour
  if( isset($_POST["start_ampm"]) && $_POST["start_ampm"]=="PM" && isset($_POST["start_hour"]) && $_POST["start_hour"]<12 ){
      $_POST["start_hour"] += 12;
  }
  if( isset($_POST["start_ampm"]) && $_POST["start_ampm"]=="AM" && isset($_POST["start_hour"]) && $_POST["start_hour"]==12 ){
      $_POST["start_hour"] = 24;

  }

  if(is_numeric($_POST["start_minute"])){
    $start_minute = $_POST["start_minute"];
  } else {
    $start_minute = "00";
  }
  $start_time = $_POST["start_hour"] .":". $start_minute;
  if(is_numeric($_POST["ending_minute"])){
    $ending_minute = $_POST["ending_minute"];
  } else {
    $ending_minute = "00";
  }
  if(is_numeric($_POST["ending_hour"])){
    if(isset($_POST["ending_ampm"]) && $_POST["ending_ampm"]=="PM"){
      $_POST["ending_hour"] += 12;
    }
	$ending_time = $_POST["ending_hour"] .":". $ending_minute; 
  } else {
    $ending_time = "";
  }

  $insertSQL = sprintf("INSERT INTO sanmig_week_class (`date`, `time`, ending, star, type, title, location, contact, website, cost, coloron, coloroff, `description`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                       GetSQLValueString($_POST['date'], "date"),
                       GetSQLValueString($start_time, "date"),
                       GetSQLValueString($ending_time, "date"),
                       GetSQLValueString($_POST['star'], "text"),
                       GetSQLValueString($_POST['type'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['location'], "text"),
                       GetSQLValueString($_POST['contact'], "text"),
                       GetSQLValueString($_POST['website'], "text"),
		       GetSQLValueString($_POST['cost'], "text"),
                       GetSQLValueString($_POST['coloron'], "text"),
                       GetSQLValueString($_POST['coloroff'], "text"),
                       GetSQLValueString($_POST['description'], "text"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($insertSQL, $sanmig) or die(mysql_error());

  $insertGoTo = "manage_ongoing_class.php";
  if (isset($_SERVER['QUERY_STRING'])) {
    $insertGoTo .= (strpos($insertGoTo, '?')) ? "&" : "?";
    $insertGoTo .= $_SERVER['QUERY_STRING'];
  }
  header(sprintf("Location: %s", $insertGoTo));
}
?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Add Regular (Ongoing) Class</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
<style>
#start_hour, #ending_hour, #start_minute, #ending_minute, .timing {display:inline; width: 50px;}
#day {width:155px;font:inherit;}
</style>

<script type="text/javascript">
<!--
// check that if they entered an ending hour, that they also
// selected AM/PM for the end time

function validateForm()
{
  var ending_hour = document.form1.ending_hour.value;
  if (ending_hour!="")
    {
	var ending_ampm = document.form1.ending_ampm.value;
	if (ending_ampm=="")
	  {
	  alert("Please set AM/PM for end time");
	  return false;
	  }
	}
}
// -->
</script>

</head>

<body>
<h1> &nbsp; Add Regular (Ongoing/Weekly) Class</h1>

<form id="form1" name="form1" method="POST" action="<?php echo $editFormAction; ?>" onSubmit="return validateForm()">
<table><tr><td>
      <label for="date" class="timing">Date:</label>
        <select name="date" id="date">
        <option value="2013-01-06">Sunday</option>
        <option value="2013-01-07">Monday</option>
        <option value="2013-01-08">Tuesday</option>
        <option value="2013-01-09">Wednesday</option>
        <option value="2013-01-10">Thursday</option>
        <option value="2013-01-11">Friday</option>
        <option value="2013-01-12">Saturday</option>
    </select>
</td><td> &nbsp; &nbsp; &nbsp; &nbsp;</td><td>
    <label for="start_hour" class="timing">Start Hour:</label>
    <select name="start_hour" id="start_hour">
	 <option value="01">1</option>
	 <option value="02">2</option>
	 <option value="03">3</option>
	 <option value="04">4</option>
	 <option value="05">5</option>
	 <option value="06">6</option>
	 <option value="07">7</option>
	 <option value="08">8</option>
	 <option value="09">9</option>
	 <option value="10">10</option>
	 <option value="11">11</option>
	 <option value="12">12</option>
	</select>
    <label for="start_minute" class="timing">Minute:</label>
	<select name="start_minute" id="start_minute">
	 <option value="00">00</option>
	 <option value="05">05</option>
	 <option value="10">10</option>
	 <option value="15">15</option>
	 <option value="20">20</option>
	 <option value="25">25</option>
	 <option value="30">30</option>
	 <option value="35">35</option>
	 <option value="40">40</option>
	 <option value="45">45</option>
	 <option value="50">50</option>
	 <option value="55">55</option>
	</select>
    <select name="start_ampm"> 
        <option value="AM">am</option>
        <option value="PM">pm</option>
    </select>&nbsp;&nbsp;12pm = noon, 12am = midnight
</td><td> &nbsp; &nbsp; &nbsp; &nbsp;</td><td>
    <label for="ending_hour" class="timing">Ending Hour:</label>
	<select name="ending_hour" id="ending_hour">
	 <option> </option>
	 <option value="01">1</option>
	 <option value="02">2</option>
	 <option value="03">3</option>
	 <option value="04">4</option>
	 <option value="05">5</option>
	 <option value="06">6</option>
	 <option value="07">7</option>
	 <option value="08">8</option>
	 <option value="09">9</option>
	 <option value="10">10</option>
	 <option value="11">11</option>
	 <option value="12">12</option>
	</select>
	<label for="ending_minute" class="timing">Minute:</label>
    <select name="ending_minute" id="ending_minute">
	 <option> </option>
	 <option value="00">00</option>
	 <option value="05">05</option>
	 <option value="10">10</option>
	 <option value="15">15</option>
	 <option value="20">20</option>
	 <option value="25">25</option>
	 <option value="30">30</option>
	 <option value="35">35</option>
	 <option value="40">40</option>
	 <option value="45">45</option>
	 <option value="50">50</option>
	 <option value="55">55</option>
	</select>
	<select name="ending_ampm">
	 <option> </option>
	 <option value="AM">am</option>
	 <option value="PM">pm</option>
    </select>&nbsp;&nbsp; optional
</td></tr></table>
<P>
<table><tr><td>
    <tr><td>  <label for="type">Spaces instead of Star:</label>
    <input name="star" type="text" value=" &nbsp; &nbsp;" id="star" size="16" maxlength="16" />

</td><td> &nbsp; &nbsp; &nbsp;</td><td>
<label for="type">Type:</label>
    <input name="type" type="text" id="type" size="11" maxlength="11" />
</td><td> &nbsp; &nbsp; &nbsp; &nbsp;</td><td>
</td><td> &nbsp; &nbsp; &nbsp; &nbsp;</td><td>
    <label for="title">Title:</label>
<input name="title" type="text" id="title" size="52" maxlength="52" />
</td><td> &nbsp; &nbsp; &nbsp; &nbsp;</td><td>
<label for="cost">Cost:</label><input name="cost" type="text" id="cost" size="52" maxlength="52" />&nbsp;&nbsp; optional
</td></tr></table>
<P>
<table><tr><td>
    <label for="location">Location:</label>
    <input name="location" type="text" id="location" size="52" maxlength="52" />
 </td><td> &nbsp; &nbsp; &nbsp; &nbsp;</td><td>
        <label for="contact">Contact:</label>
    <input name="contact" type="text" id="contact" size="52"  maxlength="52" />&nbsp;&nbsp; optional
</td><td> &nbsp; &nbsp; &nbsp; &nbsp;</td><td>
    <label for="website">Website:</label> <input name="website" type="text" id="website" size="52" maxlength="52" />&nbsp;&nbsp; optional
</td></tr></table>
<P>
<table><tr><td>

    <label for="description">Description: &nbsp;&nbsp; optional</label>
 <textarea name="description" rows="10" id="description"></textarea>
</td><td> &nbsp; &nbsp; &nbsp; &nbsp;</td><td>
    <label for="coloron">Color on (Title):</label>
    <input name="coloron" type="text" id="coloron" size="35" maxlength="35" /> &nbsp; purple = #7f00ff &nbsp;and&nbsp; red = #ee0000 &nbsp; &nbsp; &nbsp; &nbsp; font color="7f00ff"
<BR>
<img src="fonton.jpg" WIDTH="249" HEIGHT="26">

<p>
    <label for="coloroff">Color off (Title):</label>
    <input name="coloroff" type="text" id="coloroff" size="10" maxlength="10" />
<BR>
<img src="fontoff.jpg" WIDTH="64" HEIGHT="26">
</p>
  <p>
    <label for="insert"></label>
    <input type="submit" name="insert" id="insert" value="Submit" />
</p>
  <input type="hidden" name="MM_insert" value="form1" />
</form>
</td></tr></table>
</body>
</html>
