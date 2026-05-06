<?php

//--
//
if (!function_exists("GetSQLValueString")) {
	function GetSQLValueString($theValue, $theType, $theDefinedValue = "", $theNotDefinedValue = "") 
	{
		global $useThisDbHandle;
		// ( deprecated, get_magic_quotes_gpc() in 7.4 )
		//$theValue = get_magic_quotes_gpc() ? stripslashes($theValue) : $theValue;
		if( $useThisDbHandle==null ) return false;
		$theValue = function_exists("mysqli_real_escape_string") ? mysqli_real_escape_string($useThisDbHandle,$theValue) : mysqli_escape_string($useThisDbHandle,$theValue);
		
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

//--
//  return url query without ? at the beginning. 
//  if name is not found name=value is appended at the end.
//  if query is passed with http://... returned is without string before question mark "?".
function urlquery_rep_param($query="", $name="", $value="") {
	$ret="";
	$tmp="";
	$found=false;
	if(preg_match("/.*\?.*/", $query)) {
		$a=explode("?",$query); $tmp=$a[1];
	} else $tmp=$query;
	$a = explode("&",$tmp);
	/*if(count($a)==0) {
		$b=explode("=",$a[0]);
		if($b[0]==$name) {
			$found=true;
			$b[1]=$value;
		}
		$ret .= $b[0]."=".$b[1];
	} else {*/
		for($i=0; $i<count($a);$i++) {
			$b=explode("=",$a[$i]);
			if($b[0]==$name) {
				$found=true;
				$b[1]=$value;
			}
			$ret .= $b[0]."=".$b[1].($i==(count($a)-1)?"":"&");
		}
	//}
	if(!$found) {
		$ret .= ($ret==""?"?":"&").$name."=".$value;
	}
	return $ret;
}


//--
/*
 * used in:
 *   - sanmigueldeallendeevents.com/realestate/page_results.php
 *   - lokkal.com/adm/pages_order_manage.php
 * 
 * require:
 *   - $max => " how many pages is displayed in row. if max=3 return will be: <-- <- 1, 2, 3 -> --> "
 *   - $opt [
 *     - search_limit => " current limit position "
 *     - search_max   => " how many results is displayed per page "
 *     - num_results  => " number of all results "
 *     - search_query => " explode("?",basename($_SERVER['REQUEST_URI']))[1] "
 *     - search_param => " request url query parameter. Default: limit. Ex.: &limit=0 "
 *   ]
 * */
function generate_pagination($max=10, $opts=[]) {
    $g_search_limit         = $opts['search_limit'];
    $g_search_max           = $opts['search_max'];
    $numallres              = $opts['num_results'];
    $g_lastsearchparameters = $opts['search_query'];
    $g_search_param         = isset($opts['search_param'])?$opts['search_param']:"limit";
    
    //echo "d1: $numallres - $g_search_max";
    
    //       0,20,40,60          20            470          ..............
    $cur    = floor($g_search_limit / $g_search_max); //0
    $all    = ceil($numallres/$g_search_max);         //24
    $haf    = ceil($all/2);                           //12
    $hafmax = ceil($max/2);                        //10
    $i      = 0;
    $j      = $max;
    //-------------------------------------------------------------------------
    //
    $morethanmax=false;
    if($all>$max)$morethanmax=true;
    
    //# move i & j positions if current greater than half of all
    if($cur>$hafmax || $all<$max) {
		if($cur>$hafmax) $i += ($cur-$hafmax); 
		//#
		if(($j+$i)>$all)
		    $j = $all;
		else
		    $j+=$i;
		
		//#
		
	}
    //$tmp = "i: $i, <br> j: $j, <br> cur: $cur,<br> all: $all,<br> haf: $haf,<br> hafmax: $hafmax, <br> lastsearchparameters: $g_lastsearchparameters, <br>";
    
    $tmp = "<div class=\"pagination\">".($cur>0?"<a href=\"?".
        ($g_lastsearchparameters!=""?urlquery_rep_param( $g_lastsearchparameters, $g_search_param, 0):$g_search_param."=0")
        ."\"><-<-</a> &nbsp;".
        " <a href=\"?".
        ($g_lastsearchparameters!=""?urlquery_rep_param( $g_lastsearchparameters, $g_search_param, ($cur-1)*$g_search_max):$g_search_param."=".(($cur-1)*$g_search_max))
        ."\"><-</a>":"")."
        <ul class=\"\" style=\"list-style:none;display:inline-block;margin:0px;padding:0px;\">";
    for($i; $i<$j; $i++) {
		$v = ($i*$g_search_max);
		$curclass=($v==$g_search_limit?"selected":"");
		//$url = urlquery_rep_param( $g_lastsearchparameters, "limit", $v);
        $tmp .= "<li".(isset($opts['class_li'])?" class=\"".$opts['class_li']."\"":"")." style=\"display:inline-block;margin:0px 13px;\">
        <a class=\"$curclass ".(isset($opts['class_a'])?$opts['class_a']:"")."\" href=\"?".
        ($g_lastsearchparameters!=""?urlquery_rep_param( $g_lastsearchparameters, $g_search_param, $v):$g_search_param."=".$v)
        ."\">".($i+1)."</a></li>";
    }
    $tmp .= "</ul>
        ".(($morethanmax&$i<($all-1))?"<a href=\"?".
        ($g_lastsearchparameters!=""?urlquery_rep_param( $g_lastsearchparameters, $g_search_param, ($cur+1)*$g_search_max):$g_search_param."=".(($cur+1)*$g_search_max))
        ."\">-></a> &nbsp;".
        " <a href=\"?".
        ($g_lastsearchparameters!=""?urlquery_rep_param( $g_lastsearchparameters, $g_search_param, ($all-1)*$g_search_max):$g_search_param."=".(($all-1)*$g_search_max))
        ."\">->-></a>":"")."
    "."</div>";
    return $tmp;
}
?>
