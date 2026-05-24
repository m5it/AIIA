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

$currentPage = $_SERVER["PHP_SELF"];

$maxRows_getPosts = 240;
$pageNum_getPosts = 0;
if (isset($_GET['pageNum_getPosts'])) {
  $pageNum_getPosts = $_GET['pageNum_getPosts'];
}
$startRow_getPosts = $pageNum_getPosts * $maxRows_getPosts;

mysql_select_db($database_sanmig, $sanmig);
$query_getPosts = "SELECT post_id, `place`, `number`, photo, date FROM fooddrink_ads ORDER BY place, number";
$query_limit_getPosts = sprintf("%s LIMIT %d, %d", $query_getPosts, $startRow_getPosts, $maxRows_getPosts);
$getPosts = mysql_query($query_limit_getPosts, $sanmig) or die(mysql_error());
$row_getPosts = mysql_fetch_assoc($getPosts);

if (isset($_GET['totalRows_getPosts'])) {
  $totalRows_getPosts = $_GET['totalRows_getPosts'];
} else {
  $all_getPosts = mysql_query($query_getPosts);
  $totalRows_getPosts = mysql_num_rows($all_getPosts);
}
$totalPages_getPosts = ceil($totalRows_getPosts/$maxRows_getPosts)-1;

$queryString_getPosts = "";
if (!empty($_SERVER['QUERY_STRING'])) {
  $params = explode("&", $_SERVER['QUERY_STRING']);
  $newParams = array();
  foreach ($params as $param) {
    if (stristr($param, "pageNum_getPosts") == false && 
        stristr($param, "totalRows_getPosts") == false) {
      array_push($newParams, $param);
    }
  }
  if (count($newParams) != 0) {
    $queryString_getPosts = "&" . htmlentities(implode("&", $newParams));
  }
}
$queryString_getPosts = sprintf("&totalRows_getPosts=%d%s", $totalRows_getPosts, $queryString_getPosts);
?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Manage Food & Drink Ads</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
</head>

<body>
<h2> &nbsp; Manage Food & Drink Ads</h2>
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;<a href="add_fooddrink_ads.php"><FONT FACE="TREBUCHET MS" SIZE="+2" COLOR="#61B329"><B>Add a Food & Drink Ad</B></font></a> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;<a href="manage_ads.php">Ads</a> <P>
&nbsp; &nbsp; &nbsp; &nbsp;<a href="manage_onetime_event.php">Onetime Events</a>
 &nbsp; &nbsp; &nbsp; &nbsp;<a href="manage_photo_event.php">Photo Events</a>
 &nbsp; &nbsp; &nbsp; &nbsp;<a href="manage_gallery.php">Galleries</a>
 &nbsp; &nbsp; &nbsp; &nbsp;<a href="manage_ongoing_event.php">Regular (Ongoing/Weekly) Events</a>
&nbsp; &nbsp; &nbsp; &nbsp;<a href="manage_music_ads.php">Music Ads</a>
&nbsp; &nbsp; &nbsp; &nbsp;<a href="manage_magazine.php">Magazine</a></p>
  <table width="1000" border="0">
<tr>
    <th scope="col">Buy Date</th>
    <th scope="col">Place</th>
    <th scope="col">Number</th>
    <th scope="col">Photo</th>
    <th scope="col">&nbsp;</th>
    <th scope="col">&nbsp;</th>
  </tr>
  <?php do { ?>
    <tr>
      <td><?php echo $row_getPosts['date']; ?></td>
      <td><?php echo $row_getPosts['place']; ?></td>
      <td><?php echo $row_getPosts['number']; ?></td>
      <td><?php echo $row_getPosts['photo']; ?></td>
      <td><a href="update_fooddrink_ads.php?post_id=<?php echo $row_getPosts['post_id']; ?>">Edit</a></td>
      <td><a href="delete_fooddrink_ads.php?post_id=<?php echo $row_getPosts['post_id']; ?>">Delete</a></td>
    </tr>
    <?php } while ($row_getPosts = mysql_fetch_assoc($getPosts)); ?>
</table>

<table border="0">
  <tr>
    <td><?php if ($pageNum_getPosts > 0) { // Show if not first page ?>
          <a href="<?php printf("%s?pageNum_getPosts=%d%s", $currentPage, 0, $queryString_getPosts); ?>">First</a>
          <?php } // Show if not first page ?>
    </td>
    <td><?php if ($pageNum_getPosts > 0) { // Show if not first page ?>
          <a href="<?php printf("%s?pageNum_getPosts=%d%s", $currentPage, max(0, $pageNum_getPosts - 1), $queryString_getPosts); ?>">Previous</a>
          <?php } // Show if not first page ?>
    </td>
    <td><?php if ($pageNum_getPosts < $totalPages_getPosts) { // Show if not last page ?>
          <a href="<?php printf("%s?pageNum_getPosts=%d%s", $currentPage, min($totalPages_getPosts, $pageNum_getPosts + 1), $queryString_getPosts); ?>">Next</a>
          <?php } // Show if not last page ?>
    </td>
    <td><?php if ($pageNum_getPosts < $totalPages_getPosts) { // Show if not last page ?>
          <a href="<?php printf("%s?pageNum_getPosts=%d%s", $currentPage, $totalPages_getPosts, $queryString_getPosts); ?>">Last</a>
          <?php } // Show if not last page ?>
    </td>
  </tr>
</table>
<p>&nbsp;</p>
</body>
</html>
<?php
mysql_free_result($getPosts);
?>
