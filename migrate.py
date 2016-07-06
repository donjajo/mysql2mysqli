#!/usr/bin/python
import re
import sys
import os
import shutil

class MySQLize( object ):
	func = {
		'mysql_query' : [ 'mysqli_query', True ],
		'mysql_real_escape_string' : [ 'mysqli_real_escape_string', True ],
		'mysql_select_db' : [ 'mysqli_select_db', True ],
		'mysql_close' : [ 'mysqli_close', True ],
		'mysql_error' : [ 'mysqli_error', True ],
		'mysql_fetch_array' : [ 'mysqli_fetch_array' ],
		'mysql_fetch_row' : [ 'mysqli_fetch_row' ],
		'mysql_fetch_assoc' : [ 'mysqli_fetch_assoc' ],
		'mysql_num_rows' : [ 'mysqli_num_rows' ],
		'mysql_info' : [ 'mysqli_info', True ],
		'mysql_insert_id' : [ 'mysqli_insert_id', True ],
		'mysql_free_result' : 'mysqli_free_result'
	}

	def __init__( self, File, con = None, dep_con = None ):
		self.file = File
		self.dep_con = dep_con
		if os.path.isfile( File ):
			try:
				with open( File, 'r' ) as php_file:
					php_file.seek( 0 )
					self.content = php_file.read()
			except IOError as e:
				print( 'Error opening {0}: {1}'.format( File, e.args[ 1 ] ) )
		else:
			self.content = File

		if con and os.path.isfile( con ):
			with open( con, 'r' ) as f:
				self.con = self._get_con( f.read() )
		elif con is None:
			self.con = self._get_con()
		else:
			self.con = con

	def _get_con( self, content = False ):
		com = re.compile( r'(\$[a-zA-Z0-9\_].*?)mysql_[p]?connect' )
		con_var = com.findall( self.content ) if not content else com.findall( content )
	
		if con_var and re.findall( r'\=', con_var[ 0 ] ):
			return con_var[ 0 ].replace( '=', '' ).strip()
		else:
			return False

	def find_replace( self ):
		check_con = self._get_con( self.content )
		if check_con and check_con != self.con:
			replace_con = raw_input( 'Found another connection variable ({0}) in this file {1}, replace {0} with the global variable {2}? (y/N): '.format( check_con, self.file, self.con ) )
			if replace_con.lower() == 'y':
				self.con = check_con

		if not self.con:
			print( 'Unable to get connection variable' )
			sys.exit( 1 )
		for func in self.func.iterkeys():
			com = re.compile( r'{0}[\s]*?\(.*?\)'.format( re.escape( func ) ) )
			results = com.findall( self.content )
			
			if results:
				for result in results:
					args = re.findall( r'{0}[\s]*?\((.*?)[\s]*?\)[\s]*'.format( re.escape( func ) ), result )
					if re.findall( r'\"', args[ 0 ] ):
						args = args[ 0 ].strip().split( '",' )
					elif re.findall( r"\'", args[ 0 ] ):
						args = args[ 0 ].strip().split( '\',' )
					else:
				 		args = args[ 0 ].strip().split( ',' )

					args = [ x.strip() for x in args ]
					func_name = re.findall( r'([a-z_A-Z0-9]+[\s]*?)\(.*?\)', result )
					args = filter( None, args )

					if func_name:
						func_name = func_name[ 0 ].strip()
						if isinstance( self.func[ func_name ], list ) and len( self.func[ func_name ] ) > 1:
							if self.con in args:
								args.remove( self.con )
							args.insert( 0, self.con )
							if self.dep_con:
								for dep_con in self.dep_con:
									if dep_con in args:
										args.remove( dep_con )
						if len( args ) > 2:
							dep = raw_input( 'This function \n\n{0}\n\n has 2 or more arguments in {1}, one might be a connection. Enter the depreciated argument to remove: $'.format( result, self.file ) )
							dep = '${0}'.format( dep.replace( '$', '' ) )
							if dep and dep in args:
								args.remove( dep )
						self.content = re.sub( r'{0}'.format( re.escape( result ) ), '{0}( {1} )'.format( self.func[ func_name ][ 0 ], ', '.join( args ) ), self.content )
	
	def write( self ):
		path, filename = os.path.split( self.file )
		shutil.copy( self.file, '{0}.org'.format( os.path.join( path, filename ) ) )
		print( 'Writing to {0}'.format( self.file ) )
		with open( self.file, 'w' ) as f:
			f.write( self.content )

import argparse

parser = argparse.ArgumentParser( description = 'MySQL to MySQLi Migrator for PHP' )
parser.add_argument( 'file', metavar = '.php file or directory', type = str )
parser.add_argument( '--con', help = 'Connection variable, can be string as --con $con or --con /path/con.php to connect file', dest = 'con' )
parser.add_argument( '--dep', help = 'Depreciated connection variable to remove, like mysql_query( $sql, $dep_con ). --dep $dep_con or for many --dep \'$dep_con\',\'$dep_con2\'', dest = 'dep' )
g = parser.parse_args()
dep = g.dep.split( ',' ) if g.dep else []

if os.path.isdir( g.file ):
	files = list()
	for d, _, f in os.walk( '/tmp/cerebrum/' ):
		for file in f:
			if os.path.splitext( file )[ 1 ] == '.php':
				files.append( os.path.join( d, file ) )
	if files:
		for f in files:
			p = MySQLize( f, con = g.con, dep_con = dep )
			p.find_replace()
			p.write()
	else:
		print( 'No PHP files found' )
else:
	p = MySQLize( g.file, con = g.con, dep_con = dep )
	p.find_replace()
	p.write()