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
  $insertSQL = sprintf("INSERT INTO announcements (`date`, `time`, ending, pageno, pagephoto, pagetext, pagetitle, photo, title, subtitle, code) VALUES (%s, %s, %s, %s %s %s %s %s %s)",
                       GetSQLValueString($_POST['date'], "date"),
                       GetSQLValueString($_POST['time'], "date"),
                       GetSQLValueString($_POST['ending'], "text"),
                       GetSQLValueString($_POST['pageno'], "text"),
                       GetSQLValueString($_POST['pagephoto'], "text"),
                       GetSQLValueString($_POST['pagetext'], "text"),
                       GetSQLValueString($_POST['pagetitle'], "text"),
                       GetSQLValueString($_POST['photo'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['subtitle'], "text"),
                       GetSQLValueString($_POST['code'], "text"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($insertSQL, $sanmig) or die(mysql_error());

  $insertGoTo = "manage_onetime_event.php";
  if (isset($_SERVER['QUERY_STRING'])) {
    $insertGoTo .= (strpos($insertGoTo, '?')) ? "&" : "?";
    $insertGoTo .= $_SERVER['QUERY_STRING'];
  }
  header(sprintf("Location: %s", $insertGoTo));
}

if ((isset($_POST["MM_update"])) && ($_POST["MM_update"] == "form1")) {
  $updateSQL = sprintf("UPDATE announcements SET `date`=%s, `time`=%s, ending=%s, pageno=%s, pagephoto=%s, pagetext=%s, pagetitle=%s, photo=%s, title=%s, subtitle=%s, code=%s WHERE post_id=%s",
                       GetSQLValueString( (isset($_POST['date'])?$_POST['date']:""), "date"),
                       GetSQLValueString( (isset($_POST['time'])?$_POST['time']:""), "date"),
                       GetSQLValueString( (isset($_POST['ending'])?$_POST['ending']:""), "date"),
                       GetSQLValueString( (isset($_POST['pageno'])?$_POST['pageno']:""), "text"),
                       GetSQLValueString( (isset($_POST['pagephoto'])?$_POST['pagephoto']:""), "text"),
                       GetSQLValueString( (isset($_POST['pagetext'])?$_POST['pagetext']:""), "text"),
                       GetSQLValueString( (isset($_POST['pagetitle'])?$_POST['pagetitle']:""), "text"),
                       GetSQLValueString( (isset($_POST['photo'])?$_POST['photo']:""), "text"),
                       GetSQLValueString( (isset($_POST['title'])?$_POST['title']:""), "text"),
                       GetSQLValueString( (isset($_POST['subtitle'])?$_POST['subtitle']:""), "text"),
                       GetSQLValueString( (isset($_POST['code'])?$_POST['code']:""), "text"),
                       GetSQLValueString( (isset($_POST['post_id'])?$_POST['post_id']:""), "int"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($updateSQL, $sanmig) or die(mysql_error());

  $updateGoTo = "manage_announcements.php";
  if (isset($_SERVER['QUERY_STRING'])) {
    $updateGoTo .= (strpos($updateGoTo, '?')) ? "&" : "?";
    $updateGoTo .= $_SERVER['QUERY_STRING'];
  }
  header(sprintf("Location: %s", $updateGoTo));
}

$colname_getPosts = "-1";
if (isset($_GET['post_id'])) {
  $colname_getPosts = $_GET['post_id'];
}
mysql_select_db($database_sanmig, $sanmig);
$query_getPosts = sprintf("SELECT post_id, `date`, `time`, ending, pageno, pagephoto, pagetext, pagetitle, photo, title, subtitle, code FROM announcements WHERE post_id = %s", GetSQLValueString($colname_getPosts, "int"));
$getPosts = mysql_query($query_getPosts, $sanmig) or die(mysql_error());
$row_getPosts = mysql_fetch_assoc($getPosts);
$totalRows_getPosts = mysql_num_rows($getPosts);
?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Update Announcements</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
</head>

<body>
<h1> &nbsp; Update Announcements</h1>
<p>
<form id="form1" name="form1" method="POST" action="<?php echo $editFormAction; ?>">
 <p>
<table><tr><td>
    <label for="date">Date:</label>
    <input name="date" type="text" id="date" value="<?php echo $row_getPosts['date']; ?>" maxlength="10" />
  </p>
  <p>
    <label for="time">Start Time:</label>
    <input name="time" type="text" id="time" value="<?php echo $row_getPosts['time']; ?>" />
<p>
<a href="add_onetime_event.php"><FONT FACE="TREBUCHET MS" SIZE="-1" COLOR="#000000"><B>Add Onetime Event</a></B></font></a><p>purple = #7f00ff &nbsp;and&nbsp; red = #ee0000 &nbsp; &nbsp; &nbsp; &nbsp; font color="7f00ff"
<p>
    <label for="insert"></label>
    <input type="submit" name="insert" id="insert" value="Update" />
    <input name="post_id" type="hidden" id="post_id" value="<?php echo $row_getPosts['post_id']; ?>"
  </p>
</td><td> &nbsp; &nbsp; &nbsp;</td><td>
    <label for="type">Photo:</label><textarea name="photo" rows="10" id="photo"><?php echo $row_getPosts['photo']; ?></textarea>
  </p>
</td></tr></table>

  
<p>
<table><tr><td>
    <label for="title">Title:</label> <textarea name="title" rows="5" id="title"><?php echo $row_getPosts['title']; ?></textarea>
</td><td> &nbsp; &nbsp; &nbsp;</td><td>
    <label for="subtitle">Subtitle:</label>  <textarea name="subtitle" rows="2" id="subtitle"><?php echo $row_getPosts['subtitle']; ?></textarea>
  </p>
    <p>
    <label for="code">Code:</label>  <textarea name="code" rows="2" id="code"><?php echo $row_getPosts['code']; ?></textarea>
  </p>
</td></tr></table>
  <p>

    <label for="insert"></label>
    <input type="submit" name="insert" id="insert" value="Update" />
    <input name="post_id" type="hidden" id="post_id" value="<?php echo $row_getPosts['post_id']; ?>"
  </p>
  <input type="hidden" name="MM_update" value="form1" />
</form>

</body>
</html>
<?php
mysql_free_result($getPosts);
?>
