<?php 
require_once('../Connections/sanmig.php');
include "../funcs.php";

if ((isset($_GET['post_id'])) && ($_GET['post_id'] != "")) {
  $deleteSQL = sprintf("DELETE FROM photo_event WHERE post_id=%s",
                       GetSQLValueString($_GET['post_id'], "int"));

  mysqli_select_db($sanmig, $database_sanmig);
  $Result1 = mysqli_query($sanmig,$deleteSQL) or die(mysqli_error());

  $deleteGoTo = "manage_photo_event.php";
  if (isset($_SERVER['QUERY_STRING'])) {
    $deleteGoTo .= (strpos($deleteGoTo, '?')) ? "&" : "?";
    $deleteGoTo .= $_SERVER['QUERY_STRING'];
  }
  header(sprintf("Location: %s", $deleteGoTo));
}
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Delete Photo Events</title>
</head>

<body>
</body>
</html>
