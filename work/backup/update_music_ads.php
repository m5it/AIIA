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
  $insertSQL = sprintf("INSERT INTO music_ads (`place`, `number`, photo, title, subtitle, date) VALUES (%s, %s, %s, %s)",
                       GetSQLValueString($_POST['place'], "date"),
                       GetSQLValueString($_POST['number'], "date"),
                       GetSQLValueString($_POST['photo'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['subtitle'], "text"),
                       GetSQLValueString($_POST['date'], "date"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($insertSQL, $sanmig) or die(mysql_error());

  $insertGoTo = "manage_music_ads.php";
  if (isset($_SERVER['QUERY_STRING'])) {
    $insertGoTo .= (strpos($insertGoTo, '?')) ? "&" : "?";
    $insertGoTo .= $_SERVER['QUERY_STRING'];
  }
  header(sprintf("Location: %s", $insertGoTo));
}

if ((isset($_POST["MM_update"])) && ($_POST["MM_update"] == "form1")) {
  $updateSQL = sprintf("UPDATE music_ads SET `place`=%s, `number`=%s, photo=%s, title=%s, subtitle=%s, date=%s WHERE post_id=%s",
                       GetSQLValueString($_POST['place'], "text"),
                       GetSQLValueString($_POST['number'], "text"),
                       GetSQLValueString($_POST['photo'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['subtitle'], "text"),
                       GetSQLValueString($_POST['date'], "date"),
                       GetSQLValueString($_POST['post_id'], "int"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($updateSQL, $sanmig) or die(mysql_error());

  $updateGoTo = "manage_music_ads.php";
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
$query_getPosts = sprintf("SELECT post_id, `place`, `number`, photo, title, subtitle, date FROM music_ads WHERE post_id = %s", GetSQLValueString($colname_getPosts, "int"));
$getPosts = mysql_query($query_getPosts, $sanmig) or die(mysql_error());
$row_getPosts = mysql_fetch_assoc($getPosts);
$totalRows_getPosts = mysql_num_rows($getPosts);
?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Update Music Ads</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
</head>

<body>
<h1>Update Music Ads</h1>
<p><a href="index.php">Admin Menu</a></p>
<form id="form1" name="form1" method="POST" action="<?php echo $editFormAction; ?>">
  <p>
    <label for="place">Place:</label>
    <input name="place" type="text" id="place" value="<?php echo $row_getPosts['place']; ?>" maxlength="3" />
  </p>
  <p>
    <label for="number">Number:</label>
    <input name="number" type="number" id="number" value="<?php echo $row_getPosts['number']; ?>" maxlength="3" />
  </p>
  <p>
    <label for="insert"></label>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; 
    <input type="submit" name="insert" id="insert" value="Update" />
    <input name="post_id" type="hidden" id="post_id" value="<?php echo $row_getPosts['post_id']; ?>" />
  </p>
   <p>
    <label for="photo">Ad:</label> <textarea name="photo" rows="5" id="photo"><?php echo $row_getPosts['photo']; ?></textarea>
  </p>
<p>
    <label for="type">Text:</label><textarea name="title" rows="10" id="title"><?php echo $row_getPosts['title']; ?></textarea>
  </p>
  <p>
    <label for="date">Buy Date:</label>
    <input name="date" type="date" id="date" value="<?php echo $row_getPosts['date']; ?>" maxlength="10" />&nbsp;&nbsp;yyyy-mm-dd</p>
  <p>
  <p>
    <label for="subtitle">Price / Notes:</label>
    <input name="subtitle" type="subtitle" id="subtitle" value="<?php echo $row_getPosts['subtitle']; ?>" size="200" maxlength="200" />
  </p>
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
