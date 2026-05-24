<?php 
require_once('../Connections/sanmig.php');
$useThisDbHandle = $sanmig;
include "../funcs.php";

$editFormAction = $_SERVER['PHP_SELF'];
if (isset($_SERVER['QUERY_STRING'])) {
  $editFormAction .= "?" . html_entity_decode($_SERVER['QUERY_STRING']);
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

  if(is_numeric($_POST["ending_minute"]));
  if(is_numeric($_POST["ending_hour"]));
  if(isset($_POST["ending_ampm"]) && $_POST["ending_ampm"]=="PM"){
    $_POST["ending_hour"] += 12;
  }
  $ending_time = $_POST["ending_hour"] .":". $start_minute; 
  else {
    $ending_time = "";
  }


  $insertSQL = sprintf("INSERT INTO photo_event (`date`, `time`, photo, title, subtitle, code) VALUES (%s, %s, %s, %s, %s, %s)",
                       GetSQLValueString($_POST['date'], "date"),
                       GetSQLValueString($start_time, "text"),
                       GetSQLValueString($_POST['photo'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['subtitle'], "text"),
                       GetSQLValueString($_POST['code'], "text"));

  mysqli_select_db($sanmig,$database_sanmig);
  $Result1 = mysqli_query($sanmig,$insertSQL) or die(mysqli_error());

  $insertGoTo = "manage_photo_event.php";
  if (isset($_SERVER['QUERY_STRING'])) {
    $insertGoTo .= (strpos($insertGoTo, '?')) ? "&" : "?";
    $insertGoTo .= html_entity_decode($_SERVER['QUERY_STRING']);
  }
  header(sprintf("Location: %s", $insertGoTo));
}
?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Add Photo Events</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
<style>
#start_hour, #ending_hour, #start_minute, #ending_minute, .timing {display:inline; width: 50px;}
#day {width:155px;font:inherit;}
</style>
</head>

<body>
<h1> &nbsp; Post Your Photo Event</h1>
<form id="form1" name="form1" method="POST" action="<?php echo $editFormAction; ?>">
  <p>&nbsp;</p>
  <p>
    <label for="date">Date:</label>
    <input name="date" type="date" id="date" maxlength="10" />&nbsp;&nbsp;yyyy-mm-dd
  </p>
  <p>
    <label for="start_hour" class="timing">Start Hour:</label>
    <select name="start_hour" id="start_hour">
	<option value="06">6</option>
	 <option value="07">7</option>
	 <option value="08">8</option>
	 <option value="09">9</option>
	 <option value="10">10</option>
	 <option value="11">11</option>
	 <option value="12">12</option>
	 <option value="13">13</option>
	 <option value="14">14</option>
	 <option value="15">15</option>
	 <option value="16">16</option>
	 <option value="17">17</option>
	 <option value="18">18</option>
	 <option value="19">19</option>
	 <option value="20">20</option>
	 <option value="21">21</option>
	 <option value="22">22</option>
	 <option value="23">23</option>
	 <option value="24">24</option>
     <option value="01">1</option>
	 <option value="02">2</option>
	 <option value="03">3</option>
	 <option value="04">4</option>
	 <option value="05">5</option>
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
	</select><BR>For events on the same date where you <B>want</B> one event above the other:<BR>if used for events with the same date, the event with an earlier time posts higher on the page (as with other event categories, one-time and regular.)
  </p>
  
  <p>
    <label for="type">Photo:</label>
<textarea name="photo" rows="10" id="description"></textarea>
  </p>
  <p>
    <label for="title">Title:</label>
 <textarea name="title" rows="10" id="title"></textarea>
  </p>
  <p>
    <label for="subtitle">Subtitle:</label>
    <input name="subtitle" type="text" id="cost" size="200" maxlength="200" />
  </p>
     <label for="code">Code:</label>
    <input name="code" type="text" id="date" maxlength="3" />
  </p>
<p>
    <label for="insert"></label>
    <input type="submit" name="insert" id="insert" value="Submit" />
  </p>

  <p>&nbsp;</p>
  <p>&nbsp;</p>
  <input type="hidden" name="MM_insert" value="form1" />
</form>
</body>
</html>
