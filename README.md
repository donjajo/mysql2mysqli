# mysql2mysqli
Migrates PHP Depreciated functions mysql_* to mysqli_*

This package tries to convert mysql_* functions to mysqli_*. 

## Dependencies
    - Python 2.5+

## How to use
Clone or download the repository. Type 
```sh
    $ ./migrate.py --help
```
And get help options
    - --con parameter accepts the connection variable, this can be the path to the connection file and the package tries to get the variable itself. If not provided, it takes from the current file
    - --dep This is the depreciated connection variable to remove, like we have mysql_query( $query, $conn ). You supply $conn to this parameter
        ``sh
            $ ./migrate.py --dep '$conn'
        ``
        This can be null
Directory path containing PHP files can be passed as positional argument and it walks through it to modify every .php file
    ``sh
        $ ./migrate.py --con /path/to/con.php /path/to/php_project
        $ ./migrate.py '<?php $connect = mysql_connect( 'localhost', 'root', '' ); mysql_select_db( 'test' );'
        $ ./migrate.py --con '$conn' /path/to/php_project
        $ ./migrate.py file.php
        $ ./migrate.py --con /path/to/con.php /path/to/php_project --dep '$conn,$conn2'
    ``
    
