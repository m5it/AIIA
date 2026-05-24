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
<link href="../../styles/admin.css" rel="stylesheet" type="text/css" />
</head>

<body>
<h2> &nbsp; Manage Onetime Events</h2>
&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;<a href="add_onetime_event.php"><FONT FACE="TREBUCHET MS" SIZE="+2" COLOR="#EE0000"><B>Add Onetime Event</a></B></font></a><P>
&nbsp; &nbsp;<a href="manage_photo_event.php">Photo Events</a>
&nbsp; &nbsp;<a href="manage_onetime_event.php">Onetime Events</a>
&nbsp; &nbsp;<a href="manage_ongoing_event.php">Ongoing Events</a>
&nbsp; &nbsp; &nbsp;<a href="http://sanmigueldeallendeevents.com/zyxw4321/night/manage_onetime_event.php">Nightlife Events</a>
&nbsp; &nbsp; &nbsp;<a href="http://sanmigueldeallendeevents.com/zyxw4321/movie/manage_onetime_event.php">Movie Events</a>
<BR>
&nbsp; &nbsp;<a href="manage_news.php">News</a>
&nbsp; &nbsp;<a href="manage_top_posts.php">Top Posts</a>
&nbsp; &nbsp;<a href="manage_announcements.php">Announcements</a>
&nbsp; &nbsp;<a href="manage_ads.php">Event Ads</a>
&nbsp; &nbsp;<a href="manage_restaurant_ads.php">Restaurant Ads</a>
&nbsp; &nbsp;<a href="manage_music_ads.php">Nightlife Ads</a>
&nbsp; &nbsp;<a href="manage_gallery_ads.php">Gallery Ads</a>
&nbsp; &nbsp;<a href="manage_classes_ads.php">Classes Ads</a>
&nbsp; &nbsp;<a href="manage_magazine.php">Magazine</a>
&nbsp; &nbsp;<a href="http://sanmigueldeallendeevents.com/zyxw4321/manage_gallery_ads.php">Galleries</a>
&nbsp; &nbsp;<a href="http://sanmigueldeallendeevents.com/zyxw4321/tours/manage_onetime_event.php">Tours</a></p>
<table width="1000" border="0">
  <tr>
    <th scope="col">Updated</th>
    <th scope="col">Date</th>
    <th scope="col">Time</th>
    <th scope="col">Title</th>
    <th scope="col">&nbsp;</th>
    <th scope="col">&nbsp;</th>
  </tr>
  <?php do { ?>
    <tr>
      <td><?php echo $row_getPosts['updated']; ?></td>
      <td><?php echo $row_getPosts['date']; ?></td>
      <td><?php echo $row_getPosts['time']; ?></td>
      <td><?php echo $row_getPosts['title']; ?></td>
      <td><a href="update_onetime_event.php?post_id=<?php echo $row_getPosts['post_id']; ?>">Edit</a></td>
      <td><a href="delete_onetime_event.php?post_id=<?php echo $row_getPosts['post_id']; ?>">Delete</a></td>
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
