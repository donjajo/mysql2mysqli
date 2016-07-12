#!/usr/bin/python
import re
import sys
import os
import shutil

class MySQLize( object ):

	# Defining objects containing depreciated functions with the supported ones as value, the boolean value means the connection object needs to be passed
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
		"""Migrate old PHP mysql_* functions to mysqli_*"""
		self.file = File
		self.dep_con = dep_con

		# if File parameter is a file, read it!
		if self._is_file() and os.path.isfile( File ):
			try:
				with open( File, 'r' ) as php_file:
					php_file.seek( 0 )
					self.content = php_file.read()
			except IOError as e:
				print( 'Error opening {0}: {1}'.format( File, e.args[ 1 ] ) )
		else:
			# Its a string, pass it to an object
			self.content = File

		# Connection variable name provided
		if con is not None and con.startswith( '$' ):
			self.con = con
		elif con is not None and os.path.isfile( con ):
			# Connection object is a file, read and get the connection variable
			with open( con, 'r' ) as f:
				self.con = self._get_con( f.read() )
		else:
			# Connection object not given, attempt to read it from the current file
			self.con = self._get_con()

	def _is_file( self ):
		return not self.file.strip().startswith( '<?php' ) or not self.file.strip().startswith( '<?' )

	def _get_con( self, content = False ):
		"""Gets the connection variable from file or content"""
		# Compile regex for getting the variable
		com = re.compile( r'(\$[a-zA-Z0-9\_\-\>].*?)[\s]*?\=[\s]*?.[\s]*?mysql_[p]?connect' )
		con_var = com.findall( self.content ) if not content else com.findall( content )
	
		# ye! I found the variable, return it
		if con_var:
			con_var[ 0] = con_var[ 0 ].replace( '=', '' ).strip() if re.findall( r'\=', con_var[ 0 ] ) else con_var[ 0 ]
			return con_var[ 0 ]
		else:
			# Nah! I didn't :(
			return False

	def _migrate_connect( self ):
		com = re.compile( r'mysql_[p]?connect[\s]*?\((.*?)[\s]*?\)[\s]*' )
		con_args = com.findall( self.content )

		db = re.findall( r'{0}[\s]*?\((.*?)[\s]*?\)[\s]*'.format( re.escape( 'mysql_select_db' ) ), self.content )
		
		if db:
			db = db[ 0 ].strip().split( ',' )
			con_args.append( db[ 0 ] )
		con_args = [ x.strip() for x in con_args ]
		if self.con in con_args:
			con_args.remove( self.con )

		self.content = re.sub( r'mysql_[p]?connect[\s]*?\(.*?\)', '{0}( {1} )'.format( 'mysqli_connect', ', '.join( con_args ) ), self.content )

	def find_replace( self ):
		"""Main file that does the replacing of depreciated functions"""

		# Check if the current file has a connection variable that doesn't match the one provided
		check_con = self._get_con( self.content )
		if check_con and check_con != self.con:
			replace_con = raw_input( 'Found another connection variable ({0}) in this file {1}, replace {0} with the global variable {2}? (y/N): '.format( check_con, self.file, self.con ) )
			if replace_con.lower() == 'y':
				self.con = check_con

		# Wait, we don't have a connection variable. Stop!
		if not self.con:
			print( 'Unable to get connection variable, make sure the connection file path is correct' )
			sys.exit( 1 )

		self._migrate_connect()
		# Search for each depreciated functions in the file
		for func in self.func.iterkeys():
			com = re.compile( r'{0}[\s]*?\(.*?\)'.format( re.escape( func ) ) )
			results = com.findall( self.content )
			
			# Yes, we found
			if results:
				# Get the arguments of the ones we found
				for result in results:
					# Regex pattern for getting arguments from a function
					args = re.findall( r'{0}[\s]*?\((.*?)[\s]*?\)[\s]*'.format( re.escape( func ) ), result )

					# Lets not get confused with commas inside an SQL query and ones separating arguments
					if re.findall( r'\",+[^\']', args[ 0 ] ):
						args = args[ 0 ].strip().split( '",' )
						args[ 0 ] += '"'
					elif re.findall( r"\',+[^\"]", args[ 0 ] ):
						args = args[ 0 ].strip().split( '\',' )
						args[ 0 ] += '\''
					else:
				 		args = args[ 0 ].strip().split( ',' )

				 	# Sanitize arguments
					args = [ x.strip() for x in args ]

					# Find the function name only from depreciated functions found in file
					func_name = re.findall( r'([a-z_A-Z0-9]+[\s]*?)\(.*?\)', result )

					# Remove empty argument values
					args = filter( None, args )

					# We have the function name
					if func_name:
						func_name = func_name[ 0 ].strip()

						# We are checking if the replacement for the depreciated function should have a connection variable as argument
						if len( self.func[ func_name ] ) > 1:
							# Connection variable already existing in arguments? Remove it
							if self.con in args:
								args.remove( self.con )
							# Then add it again, having the index of 0
							args.insert( 0, self.con )
							
							# If any depreciated connection variable provided, remove it and stop asking
							if self.dep_con:
								for dep_con in self.dep_con:
									if dep_con in args:
										args.remove( dep_con )

						# mysql_* functions mostly have 2 arguments, if its more than 2; prompt the user
						if len( args ) > 2:
							dep = raw_input( 'This function \n\n{0}\n\n has 2 or more arguments in {1}, one might be a connection. Enter the depreciated argument to remove or leave empty: $'.format( result, self.file ) )
							dep = '${0}'.format( dep.replace( '$', '' ) )
							if dep and dep in args:
								args.remove( dep )

						# Finally do the replacement
						self.content = re.sub( r'{0}'.format( re.escape( result ) ), '{0}( {1} )'.format( self.func[ func_name ][ 0 ], ', '.join( args ) ), self.content )
	
	def write( self ):
		"""Writes back to the PHP file and creates backup"""
		if os.path.isfile( self.file ):
			# Get path name and .php file name
			path, filename = os.path.split( self.file )
			
			# Create backup
			backup = '{0}.org'.format( os.path.join( path, filename ) )
			print( 'Backing up {0} -> {1}'.format( self.file, backup ) )
			shutil.copy( self.file, backup )
			print( 'Migrating {0}'.format( self.file ) )
			with open( self.file, 'w' ) as f:
				f.write( self.content )
				print( 'Done!\n' );
		else:
			print( self.content )
			sys.exit( 1 )

if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser( description = 'MySQL to MySQLi Migrator for PHP' )
	parser.add_argument( 'file', metavar = '.php file or directory', type = str )
	parser.add_argument( '--con', help = 'Connection variable, can be string as --con $con or --con /path/con.php to connect file', dest = 'con' )
	parser.add_argument( '--dep', help = 'Depreciated connection variable to remove, like mysql_query( $sql, $dep_con ). --dep $dep_con or for many --dep \'$dep_con\',\'$dep_con2\'', dest = 'dep' )
	g = parser.parse_args()
	dep = g.dep.split( ',' ) if g.dep else []

	if os.path.isdir( g.file ):
		files = list()
		for d, _, f in os.walk( g.file ):
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