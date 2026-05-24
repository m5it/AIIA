<?php
//echo "d1";
//--
//error_reporting(E_ALL);
//ini_set('display_errors', 'On');

require_once('../Connections/sanmig.php'); 
?>
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
$query_getPosts = "SELECT post_id, `date`, `time`, code, title, updated FROM top_posts WHERE top_posts.`date`> '01-10-31' ORDER BY top_posts.`date` DESC, top_posts.`time` DESC";
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
<title>Top Posts Manage</title>
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
</head>

<body>
<h2> &nbsp; Manage Top Posts</h2>
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;<a href="add_top_posts.php"><FONT FACE="TREBUCHET MS" SIZE="+2" COLOR="#1E90FF"><B>Add Top Post</a></B></font></a>&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;<a href="add_onetime_event.php"><FONT FACE="TREBUCHET MS" SIZE="-1" COLOR="#000000"><B>Add Onetime Event</a></B></font></a>  <P>
&nbsp; &nbsp;<a href="manage_photo_event.php">Photo Events</a>
&nbsp; &nbsp;<a href="manage_onetime_event.php">Onetime Events</a>
&nbsp; &nbsp;<a href="manage_ongoing_event.php">Ongoing Events</a>
&nbsp; &nbsp; &nbsp;<a href="http://sanmigueldeallendeevents.com/zyxw4321/night/manage_ongoing_event.php">Nightlife Events</a>
&nbsp; &nbsp; &nbsp;<a href="http://sanmigueldeallendeevents.com/zyxw4321/movie/manage_onetime_event.php">Movie Events</a>
&nbsp; &nbsp; &nbsp;<a href="https://sanmigueldeallendeevents.com/zyxw4321/manage_class.php">Classes</a>
&nbsp; &nbsp;<a href="manage_ongoing_class.php">Ongoing Classes</a>
<BR>
&nbsp; &nbsp;<a href="manage_news.php">News</a>
&nbsp; &nbsp;<a href="manage_top_posts.php">Top Posts</a>
&nbsp; &nbsp;<a href="manage_announcements.php">Announcements</a>
&nbsp; &nbsp;<a href="manage_ads.php">Event Ads</a>
&nbsp; &nbsp;<a href="manage_restaurant_ads.php">Restaurant Ads</a>
&nbsp; &nbsp;<a href="manage_restaurant_ads_sac.php">Salida a Celaya Ads</a>
&nbsp; &nbsp;<a href="manage_music_ads.php">Nightlife Ads</a>
&nbsp; &nbsp;<a href="manage_gallery_ads.php">Gallery Ads</a>
&nbsp; &nbsp;<a href="manage_classes_ads.php">Classes Ads</a>
&nbsp; &nbsp;<a href="manage_magazine.php">Magazine</a>
&nbsp; &nbsp;<a href="http://sanmigueldeallendeevents.com/zyxw4321/manage_gallery_ads.php">Galleries</a>
&nbsp; &nbsp;<a href="http://sanmigueldeallendeevents.com/zyxw4321/tours/manage_onetime_event.php">Tours</a><BR>
&nbsp; &nbsp;<a href="manage_restaurant.php">Salida a Celaya Listing</a></p>



<table width="1000" border="0">
  <tr>
    <th scope="col">Updated</th>
    <th scope="col">Date</th>
    <th scope="col">Time</th>
    <th scope="col">Title</th>
    <th scope="col">code</th>
    <th scope="col">&nbsp;</th>
  </tr>
  <?php do { ?>
    <tr>
      <td><?php echo $row_getPosts['updated']; ?></td>
      <td><?php echo $row_getPosts['date']; ?></td>
      <td><?php echo $row_getPosts['time']; ?></td>
      <td><?php echo $row_getPosts['title']; ?></td>
      <td> &nbsp; <?php echo $row_getPosts['code']; ?></td>
<td><a href="update_top_posts.php?post_id=<?php echo $row_getPosts['post_id']; ?>">Edit</a></td>
      <td><a href="delete_top_posts.php?post_id=<?php echo $row_getPosts['post_id']; ?>">Delete</a></td>
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
