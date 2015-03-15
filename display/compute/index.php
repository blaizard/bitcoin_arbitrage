<html>
	<head>
		<meta http-equiv="refresh" content="1">
	</head>
	<body>
		<pre><?php
			$result = @file_get_contents("display.txt");
			if ($result == false) {
				echo "Reloading...";
			}
			else {
				echo htmlentities($result);
			}
		?>
		</pre>
	</body>
</html>
