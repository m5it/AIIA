<?php 
/*test*/
require_once('../Connections/sanmig.php');

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


  $insertSQL = sprintf("INSERT INTO restaurant (`place`, `number`, photo, title, subtitle, pagetext) VALUES (%s, %s, %s, %s, %s, %s)",
                       GetSQLValueString($_POST['place'], "text"),
                       GetSQLValueString($_POST['number'], "text"),
                       GetSQLValueString($_POST['photo'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['subtitle'], "text"),
                       GetSQLValueString($_POST['pagetext'], "text"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($insertSQL, $sanmig) or die(mysql_error());

  $insertGoTo = "manage_restaurant.php";
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
<title>Add Restaurant Listing</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
<style>
#start_hour, #ending_hour, #start_minute, #ending_minute, .timing {display:inline; width: 50px;}
#day {width:155px;font:inherit;}
</style>
</head>

<body>
<h1> &nbsp; Add Restaurant Listing</h1>
<form id="form1" name="form1" method="POST" action="<?php echo $editFormAction; ?>">
 <TABLE><TR><TD>

</TD><TD>  

    <label for="place">Place:</label>
    <input name="place" type="text" id="place" maxlength="4" />
  &nbsp; &nbsp; &nbsp;
  </td>

  <td>
       <label for="number">Number:</label>
    <input name="number" type="number" id="number" maxlength="4" />
  </TD>
<td>
 &nbsp; &nbsp; &nbsp; &nbsp;  
  </TD>

<td>
<label for="insert"></label>
    <input type="submit" name="insert" id="insert" value="Submit" />
</TD>
</TR></TABLE>
  
<TABLE><TR><TD> 
    <label for="type">Photo:</label>
<textarea name="photo" rows="10" id="description"></textarea>
</TD><TD>
    <label for="title">Restaurant Name:</label>
 <textarea name="title" rows="10" id="title"></textarea>
</TD>
</TR></TABLE>
  <p>
   <TABLE><TR><TD> 
    <label for="subtitle">Contact:</label>
<textarea name="subtitle" rows="10" id="description"></textarea>
</TD><TD>
    <label for="title">Description:</label>
 <textarea name="pagetext" rows="10" id="pagetext"></textarea>
</TD>
</TR></TABLE>


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
