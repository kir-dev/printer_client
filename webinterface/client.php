<?php
// Included vars: $host, $user, $pass, $db
require_once('db.php');

header('Content-Type: text/plain; charset=utf-8');

function printError($msg) {
	print "error=$msg\n";
	exit();
}

function internalError() {
	printError('Ismeretlen hiba!');
}

function appkeyError() {
	print "special=appkey";
	exit();
}

$my = new mysqli($host, $user, $pass, $db);

if (!empty($my->connect_error)) {
	internalError();
}

$my->set_charset('utf8');

//Required variable:
if (!isset($_POST['appkey']) || !isset($_POST['version'])) {
	internalError();
}

$ver = explode(".", $_POST['version']);

$release = 0;
$major = 2;
$minor = 0;

if ($ver[0] < $release ||
	$ver[0] == $release && $ver[1] < $major ||
	$ver[0] == $release && $ver[1] == $major && $ver[2] < $minor) {
	//Update required

	print "special=update\n";
	exit();
}

if (isset($_POST['status']) && isset($_POST['printer'])) {
	//Acceptable values
	if (!($_POST['status'] == 'on' || $_POST['status'] == 'off')) {
		internalError();
	}
	$status = $_POST['status'];
	$printer = $_POST['printer'];
}

//TODO: check AppKey format too

$appkey = $_POST['appkey'];


$st = $my->prepare("SELECT uid, nick FROM users WHERE appkey = ?");
$st->bind_param('s', $appkey);
$st->execute();
$st->bind_result($userID, $name);

$count = 0;
while($st->fetch()) $count++;
if ($count == 0) {
	appkeyError();
}
else if ($count > 1) {
	internalError();
}
$st->close();


if (isset($status)) {
	$st = $my->prepare("UPDATE `printers` SET `on` = ?, `last_refreshed`=NOW() WHERE `uid` = ? AND `id` = ?");
	$bStatus = ($status == 'on');
	$st->bind_param('isi', $bStatus, $userID, $printer);
	$st->execute();

	if ($st->affected_rows > 1) {
		internalError();
	}

	//If everything is OK, return with the updated status
	print "status=$status\n";

	$st->close();
}
else {
	print "name=$name\n";

	$st = $my->prepare("SELECT `id`, `type`, `model`, `loc`, `on` FROM `printers` WHERE `uid` = ?");
	$st->bind_param('s', $userID);
	$st->execute();
	$st->bind_result($pId, $pType, $pModel, $pRoom, $pStatus);
	$i = 0;
	while ($st->fetch()) {
		print "printer_{$i}_id=$pId\n";
		//TODO: nyomtató típusok elnevezése
		print "printer_{$i}_name=$pModel ($pType) - szobaszám: $pRoom\n";
		printf("printer_{$i}_status=%s\n", $pStatus ? 'on' : 'off');
		++$i;
	}
	$st->close();
}
$my->close();


?>