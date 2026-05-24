<?php 
require_once('../Connections/sanmig.php');
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


  $insertSQL = sprintf("INSERT INTO magazine (`date`, `time`, photo, title, subtitle, code) VALUES (%s, %s, %s, %s, %s, %s)",
                       GetSQLValueString($_POST['date'], "date"),
                       GetSQLValueString($start_time, "text"),
                       GetSQLValueString($_POST['photo'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['subtitle'], "text"),
                       GetSQLValueString($_POST['code'], "text"));

  mysqli_select_db($sanmig,$database_sanmig);
  $Result1 = mysqli_query($sanmig,$insertSQL) or die(mysqli_error());

  $insertGoTo = "manage_magazine.php";
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
<title>Add Magazine Article</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
<style>
#start_hour, #ending_hour, #start_minute, #ending_minute, .timing {display:inline; width: 50px;}
#day {width:155px;font:inherit;}
</style>
</head>

<body>
<h1> &nbsp; Post Your Magazine Article</h1>
<form id="form1" name="form1" method="POST" action="<?php echo $editFormAction; ?>">
  <p>&nbsp;</p>
  <p>
    <label for="date">Date:</label>
    <input name="date" type="date" id="date" maxlength="10" />&nbsp;&nbsp;yyyy-mm-dd
  </p>
  <p>
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
    </select><BR>Time is optional here. Use only for events on the same date where you <B>want</B> one event above the other.<BR>If used for events with the same date, the event with an earlier time posts higher on the page (as with other event categories.)<BR>12pm = noon,  12am = midnight
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
    <input name="code" type="code" id="date" maxlength="3" />
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
