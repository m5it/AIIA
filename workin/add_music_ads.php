<?php 
//require_once('../Connections/sanmig.php');
include "../Connections/sanmig-29.10.16.php";

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
  /*$start_time    = "";
  $start_hour    = 0;
  $start_minute  = "";
  $ending_time   = "";
  $ending_hour   = 0;
  $ending_minute = "";
  
  # Update time to 24 hour
  if( isset($_POST["start_ampm"]) && $_POST["start_ampm"]=="PM" && isset($_POST["start_hour"]) && $_POST["start_hour"]<12 ){
      $start_hour = $_POST['start_hour'];
      $start_hour += 12;
  }
  if( isset($_POST["start_ampm"]) && $_POST["start_ampm"]=="AM" && isset($_POST["start_hour"]) && $_POST["start_hour"]==12 ){
      $start_hour = $_POST['start_hour'];
      $start_hour = 24;
  }

  if(isset($_POST['start_minute']) && is_numeric($_POST["start_minute"])){
    $start_minute = $_POST["start_minute"];
  } else {
    $start_minute = "00";
  }
  $start_time = $start_hour.":". $start_minute;

  if(isset($_POST['ending_minute']) && is_numeric($_POST["ending_minute"])){
    $ending_minute = $_POST["ending_minute"];
  } else $ending_minute = "00";
  
  if(isset($_POST['ending_hour']) && is_numeric($_POST["ending_hour"])){
      if(isset($_POST["ending_ampm"]) && $_POST["ending_ampm"]=="PM"){
	      $ending_hour = $_POST['ending_hour'];
          $ending_hour += 12;
      }
	  $ending_time = $ending_hour.":". $ending_minute; 
  } else $ending_time = "";

  
    echo "Debug: <br>
    start_hour: $start_hour<br>
    start_minute: $start_minute<br>
    start_time: $start_time<br>
    ending_hour: $ending_hour<br>
    ending_minute: $ending_minute<br>
    ending_time: $ending_time<br>
    ";*/
  /*$insertSQL = sprintf("INSERT INTO music_ads (`place`, `number`, photo, title, subtitle, date) VALUES (%s, %s, %s, %s, %s, %s)",
                       GetSQLValueString($_POST['place'], "text"),
                       GetSQLValueString($_POST['number'], "text"),
                       GetSQLValueString($_POST['photo'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['subtitle'], "text"),
                       GetSQLValueString($_POST['date'], "date"));*/

  mysqli_select_db($sanmig, $database_sanmig);
  $q = "INSERT INTO music_ads (`place`, `number`, photo, title, subtitle, date) VALUES (".
               "'".mysqli_real_escape_string($sanmig,$_POST['place'])."',".
               "'".mysqli_real_escape_string($sanmig,$_POST['number'])."',".
               "'".mysqli_real_escape_string($sanmig,$_POST['photo'])."',".
               "'".mysqli_real_escape_string($sanmig,$_POST['title'])."',".
               "'".mysqli_real_escape_string($sanmig,$_POST['subtitle'])."',".
               "'".mysqli_real_escape_string($sanmig,$_POST['date'])."'".
                ");";
  mysqli_query($sanmig, $q) or die(mysqli_error());

  $goto = "manage_music_ads.php";
  if (isset($_SERVER['QUERY_STRING'])) {
    $goto .= (strpos($goto, '?')) ? "&" : "?";
    $goto .= $_SERVER['QUERY_STRING'];
  }
  header("Location: $goto");

}
?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Add Music Ads</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
<style>
#start_hour, #ending_hour, #start_minute, #ending_minute, .timing {display:inline; width: 50px;}
#day {width:155px;font:inherit;}
</style>
</head>

<body>
<h1> &nbsp; Add Music Ad</h1>
<form id="form1" name="form1" method="POST" action="<?php echo $editFormAction; ?>">
  <p>
    <label for="place">Place:</label>
    <input name="place" id="place" maxlength="3" />
  </p>
  <p>
    <label for="number">Number:</label>
    <input name="number" type="number" id="number" maxlength="3" />
  </p>
  <p>
    <label for="photo">Ad:</label>
 <textarea name="photo" rows="10" id="photo"></textarea>
  </p>
  <p>
    <label for="insert"></label> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;
    <input type="submit" name="insert" id="insert" value="Submit" />
  </p>
    <p>
    <label for="title">Text:</label>
<textarea name="title" rows="10" id="title"></textarea>
  </p>
  <p>
    <label for="date">Buy Date:</label>
    <input name="date" type="date" id="date" maxlength="10" />&nbsp;&nbsp;yyyy-mm-dd
  </p>
  <p>
    <label for="subtitle">Price / Notes:</label>
    <input name="subtitle" type="subtitle" id="subtitle" size="200" maxlength="200" />
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
