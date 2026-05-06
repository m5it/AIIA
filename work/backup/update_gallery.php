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
  $insertSQL = sprintf("INSERT INTO galleries (`time`, buydate, type, title, hours, location, contact, website, coloron, coloroff, `description`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                       
                       GetSQLValueString($_POST['time'], "date"),
                       GetSQLValueString($_POST['buydate'], "date"),
                       GetSQLValueString($_POST['type'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['hours'], "text"),
                       GetSQLValueString($_POST['location'], "text"),
                       GetSQLValueString($_POST['contact'], "text"),
                      GetSQLValueString($_POST['website'], "text"),
                      GetSQLValueString($_POST['coloron'], "text"),
                      GetSQLValueString($_POST['coloroff'], "text"),
                       GetSQLValueString($_POST['description'], "text"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($insertSQL, $sanmig) or die(mysql_error());

  $insertGoTo = "manage_gallery.php";
  if (isset($_SERVER['QUERY_STRING'])) {
    $insertGoTo .= (strpos($insertGoTo, '?')) ? "&" : "?";
    $insertGoTo .= $_SERVER['QUERY_STRING'];
  }
  header(sprintf("Location: %s", $insertGoTo));
}

if ((isset($_POST["MM_update"])) && ($_POST["MM_update"] == "form1")) {
  $updateSQL = sprintf("UPDATE galleries SET `time`=%s, buydate=%s, type=%s, title=%s, hours=%s, location=%s, contact=%s, website=%s, coloron=%s, coloroff=%s, `description`=%s WHERE post_id=%s",
                      
                       GetSQLValueString($_POST['time'], "date"),
                       GetSQLValueString($_POST['buydate'], "date"),
                       GetSQLValueString($_POST['type'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['hours'], "text"),
                       GetSQLValueString($_POST['location'], "text"),
                       GetSQLValueString($_POST['contact'], "text"),
                       GetSQLValueString($_POST['website'], "text"),
                       GetSQLValueString($_POST['coloron'], "text"),
                      GetSQLValueString($_POST['coloroff'], "text"),
                       GetSQLValueString($_POST['description'], "text"),
                       GetSQLValueString($_POST['post_id'], "int"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($updateSQL, $sanmig) or die(mysql_error());

  $updateGoTo = "manage_gallery.php";
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
$query_getPosts = sprintf("SELECT post_id, `time`, buydate, type, title, location, contact, website, hours, coloron, coloroff, `description` FROM galleries WHERE post_id = %s", GetSQLValueString($colname_getPosts, "int"));
$getPosts = mysql_query($query_getPosts, $sanmig) or die(mysql_error());
$row_getPosts = mysql_fetch_assoc($getPosts);
$totalRows_getPosts = mysql_num_rows($getPosts);
?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Update Gallery</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
</head>

<body>
<h1> &nbsp; Update Gallery</h1>
<p><a href="index.php">Admin Menu</a></p>
<form id="form1" name="form1" method="POST" action="<?php echo $editFormAction; ?>">
  <p>
    <label for="date">Exhibit Expiration Date:</label>
    <input name="date" type="text" id="date" value="<?php echo $row_getPosts['date']; ?>" maxlength="10" /> &nbsp; &nbsp; yyyy-mm-dd
  </p>


<p>
    <label for="type">Type:</label>
    <input name="type" type="text" id="type" value="<?php echo $row_getPosts['type']; ?>" maxlength="3" />


    <label for="insert"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;</label>
     &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;   &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;   &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;  
    <input type="submit" name="insert" id="insert" value="Update" /> &nbsp; Is all the info updated? &nbsp; There is a another Update button below.
    <input name="post_id" type="hidden" id="post_id" value="<?php echo $row_getPosts['post_id']; ?>" />


    <label for="title">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; Title:</label>
    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <input name="title" type="text" id="title" value="<?php echo $row_getPosts['title']; ?>" size="68" maxlength="68" />
  </p>
    <p>
    <label for="location">Location:</label>
    <input name="location" type="text" id="location" value="<?php echo $row_getPosts['location']; ?>" size="200" maxlength="200" />
  </p>
    <label for="hours">Hours:</label>
    <input name="hours" type="text" id="hours" value="<?php echo $row_getPosts['hours']; ?>" size="200" maxlength="200" />
  </p>
  <p>
    <label for="contact">Contact:</label>
    <input name="contact" type="text" id="contact" value="<?php echo $row_getPosts['contact']; ?>" size="200" maxlength="200" />
  </p>
    <p>
    <label for="website">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; Website:</label>
    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <input name="website" type="text" id="website" value="<?php echo $row_getPosts['website']; ?>" size="52" maxlength="52" />
  </p>

<p>
    <label for="description">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; Description:</label>
    &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <textarea name="description" rows="10" id="description"><?php echo $row_getPosts['description']; ?></textarea>
  </p>
    <label for="insert"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;</label>
     &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;   &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;   &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;  
    <input type="submit" name="insert" id="insert" value="Update" /> &nbsp; Is all the info updated? &nbsp; There is a another Update button below.
    <input name="post_id" type="hidden" id="post_id" value="<?php echo $row_getPosts['post_id']; ?>" />
<p>
       <label for="coloron"> Color on (Title):</label> <textarea name="coloron" rows="10" id="coloron"><?php echo $row_getPosts['coloron']; ?></textarea> &nbsp; purple = #7f00ff &nbsp;and&nbsp; red = #ee0000 &nbsp; &nbsp; &nbsp; &nbsp; font color="7f00ff"
<BR>
<img src="fonton.jpg" WIDTH="249" HEIGHT="26"><P>
    <label for="coloroff">Color off (Title):</label>
    <input name="coloroff" type="text" id="coloroff" value="<?php echo $row_getPosts['coloroff']; ?>" size="10" maxlength="10" /><BR>
<img src="fontoff.jpg" WIDTH="64" HEIGHT="26">
</p>
  <p>
    <label for="insert"></label>
    <input type="submit" name="insert" id="insert" value="Update" />
    <input name="post_id" type="hidden" id="post_id" value="<?php echo $row_getPosts['post_id']; ?>" />
  </p>
  <input type="hidden" name="MM_update" value="form1" />
</form>

</body>
</html>
<?php
mysql_free_result($getPosts);
?>
