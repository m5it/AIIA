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
  $insertSQL = sprintf("INSERT INTO sanmig (`date`, `time`, ending, star, type, title, cost, location, contact, website, coloron, coloroff, `description`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                       GetSQLValueString($_POST['date'], "date"),
                       GetSQLValueString($_POST['time'], "date"),
                       GetSQLValueString($_POST['ending'], "date"),
                       GetSQLValueString($_POST['star'], "text"),
                       GetSQLValueString($_POST['type'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['cost'], "text"),
                       GetSQLValueString($_POST['location'], "text"),
                       GetSQLValueString($_POST['contact'], "text"),
                      GetSQLValueString($_POST['website'], "text"),
                      GetSQLValueString($_POST['coloron'], "text"),
                      GetSQLValueString($_POST['coloroff'], "text"),
                       GetSQLValueString($_POST['description'], "text"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($insertSQL, $sanmig) or die(mysql_error());

  $insertGoTo = "Smanage_onetime_event.php";
  if (isset($_SERVER['QUERY_STRING'])) {
    $insertGoTo .= (strpos($insertGoTo, '?')) ? "&" : "?";
    $insertGoTo .= $_SERVER['QUERY_STRING'];
  }
  header(sprintf("Location: %s", $insertGoTo));
}

if ((isset($_POST["MM_update"])) && ($_POST["MM_update"] == "form1")) {
  $updateSQL = sprintf("UPDATE sanmig SET `date`=%s, `time`=%s, ending=%s, star=%s, type=%s, title=%s, cost=%s, location=%s, contact=%s, website=%s, coloron=%s, coloroff=%s, `description`=%s WHERE post_id=%s",
                       GetSQLValueString($_POST['date'], "date"),
                       GetSQLValueString($_POST['time'], "date"),
                       GetSQLValueString($_POST['ending'], "text"),
                       GetSQLValueString($_POST['star'], "text"),
                       GetSQLValueString($_POST['type'], "text"),
                       GetSQLValueString($_POST['title'], "text"),
                       GetSQLValueString($_POST['cost'], "text"),
                       GetSQLValueString($_POST['location'], "text"),
                       GetSQLValueString($_POST['contact'], "text"),
                       GetSQLValueString($_POST['website'], "text"),
                       GetSQLValueString($_POST['coloron'], "text"),
                      GetSQLValueString($_POST['coloroff'], "text"),
                       GetSQLValueString($_POST['description'], "text"),
                       GetSQLValueString($_POST['post_id'], "int"));

  mysql_select_db($database_sanmig, $sanmig);
  $Result1 = mysql_query($updateSQL, $sanmig) or die(mysql_error());

  $updateGoTo = "Smanage_onetime_event.php";
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
$query_getPosts = sprintf("SELECT post_id, `date`, `time`, ending, star, type, title, location, contact, website, cost, coloron, coloroff, `description` FROM sanmig WHERE post_id = %s", GetSQLValueString($colname_getPosts, "int"));
$getPosts = mysql_query($query_getPosts, $sanmig) or die(mysql_error());
$row_getPosts = mysql_fetch_assoc($getPosts);
$totalRows_getPosts = mysql_num_rows($getPosts);
?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Actualizar Evento</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
</head>

<body>
<h1> &nbsp; Actualizar Evento</h1>
<form id="form1" name="form1" method="POST" action="<?php echo $editFormAction; ?>">
  <p>
<table><tr><td>
    <label for="date">Fecha:</label>
    <input name="date" type="text" id="date" value="<?php echo $row_getPosts['date']; ?>" maxlength="10" /> &nbsp;aaaa-mm-dd
</td><td>&nbsp; &nbsp; &nbsp; </td><td>
    <label for="time">Comienza:</label>
    <input name="time" type="text" id="time" value="<?php echo $row_getPosts['time']; ?>" /> &nbsp; 
</td><td>&nbsp; &nbsp; &nbsp; </td><td>
      <label for="ending">Finaliza:</label>
<input name="ending" type="text" id="ending" value="<?php echo $row_getPosts['ending']; ?>" /> 
</td></tr></table>
</p>

<p>
<table><tr><td>&nbsp; &nbsp; &nbsp; </td><td>
    <label for="type">Tipo:</label>
    <input name="type" type="text" id="type" value="<?php echo $row_getPosts['type']; ?>" maxlength="8" />
</td><td>&nbsp; &nbsp; &nbsp; </td><td>
    <label for="title">Titulo:</label>
<input name="title" type="text" id="title" value="<?php echo $row_getPosts['title']; ?>" size="52" maxlength="52" />
</td><td>&nbsp; &nbsp; &nbsp; </td><td>
    <label for="location">Ubicaci&oacute;n:</label>
    <input name="location" type="text" id="location" value="<?php echo $row_getPosts['location']; ?>" size="52" maxlength="52" />
  </td></tr></table>
</p>
  <p>
<table><tr><td>   
 <label for="cost">Costo:</label>
 <input name="cost" type="text" id="cost" value="<?php echo $row_getPosts['cost']; ?>" size="52" maxlength="52" />
</td><td>&nbsp; &nbsp; &nbsp; </td><td>
    <label for="contact">Contacto:</label>
    <input name="contact" type="text" id="contact" value="<?php echo $row_getPosts['contact']; ?>" size="52" maxlength="52" />
</td><td>&nbsp; &nbsp; &nbsp; </td><td>
    <label for="website">Sitio Web:</label>
   <input name="website" type="text" id="website" value="<?php echo $row_getPosts['website']; ?>" size="52" maxlength="52" />
 </td></tr/></table>
 </p>

<p>
<table><tr><td>
    <label for="description">Descripci&oacute;n:</label>
   <textarea name="description" rows="10" id="description"><?php echo $row_getPosts['description']; ?></textarea>
</td></tr></table>
</p>
<p>
<table><tr><td>
    <label for="insert"></label>
    <input type="submit" name="insert" id="insert" value="Actualizar" />
    <input name="post_id" type="hidden" id="post_id" value="<?php echo $row_getPosts['post_id']; ?>" />
  </p>
  <input type="hidden" name="MM_update" value="form1" />
</form>
</td></tr></table>
</body>
</html>
<?php
mysql_free_result($getPosts);
?>
