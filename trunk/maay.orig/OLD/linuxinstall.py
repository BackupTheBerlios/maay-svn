"""
  Module <linuxmaayrun>
"""

import os
import sys
import getopt
import MySQLdb
import time

import maay.constants
import maay.maaymain


def prompt_info (msg, default=None):

        if default:
                prompt = "%s [%s]:" % (msg, default)
        else:
                prompt = "%s:" % (msg,)
        ret = None
        while not ret:
                ret = raw_input(prompt) or default

        return ret



def install_db():
        """
        interactive creation of maay user, database and tables
        """

        while 1:
                superuser = prompt_info ("Enter the name of a MySQL super-user", "root") 
	        superuser_passwd = prompt_info ("Enter the password of a MySQL super-user")
                try:
                        connection = MySQLdb.Connect(
                                        user=superuser, 
                                        passwd=superuser_passwd, 
                                        db="mysql")
                except DatabaseError, msg:
                        print "connection failed: " + msg

        # create database
        cursor = None
        db = None
        db = raw_input("Enter the name of the database to create [maay]: ") or "maay"
        exist = 0
        try:
                connection.select_db(db)
                exist = 1
        except Exception, e:
                pass

        if not exist:
                choice = raw_input("Database already exist; drop ? [y/N]")
                if erase == "y":
                        cursor = connection.cursor()
                        cursor.execute("DROP DATABASE %s" % db)
                        print "database dropped"
                        break
                else:
                        print "using existing database"


	connection.select_db("mysql")
	cursor = connection.cursor()

	cursor.execute("CREATE DATABASE %s" % db)


	user = None
	user_password = None

	while 1:
		user = raw_input("Enter the name of the user which access to maay database [%s]: " % db) or db
		exist = 0

		cursor.execute("SELECT user FROM user WHERE user='%s'" % user)
		row = cursor.fetchone()

		if row:
			use = raw_input("User already exist it, use it [y/N]")
			if use == "y":
				break
		else:
			break

	user_password = raw_input("Enter the password: ") 

	connection.select_db(db)
	cursor = connection.cursor()
	cursor.execute('GRANT ALL ON *.* TO "%s"@"localhost" IDENTIFIED BY "%s" WITH GRANT OPTION' % (user, user_password))
	connection.close()

	database = maay.database.Database('mysql', host='localhost', user=user,passwd=user_password,db=db)
	database.create_tables()
	database.close()

	config_file = raw_input("Write database config file [config/db.conf] : ") or "config/db.conf"

	fd = open(config_file, 'w')
	fd.write("""# DATABASE CONFIG FILE GENERATED WITH install_db.sh

	Dbms mysql
	MySQLHost localhost
	MySQLPort 3306
	MySQLUser %s
	MySQLPassword %s
	MySQLDatabase %s""" %(user, user_password,db))
	fd.close()

print_help = 0
# checking arguments
try:
	options, arguments = getopt.getopt(sys.argv[1:], 'h')
	if options and options[0] == '-h':
		print_help = 1
	elif len(arguments) > 1:
		print "Syntax error"
		print_help = 1				
	elif len(arguments) == 0:
		action = "start"
	else:
		action = arguments[0]		
		if not action in ('install_db', 'reset_db', 'start'):
			print "Syntax error"
			print_help = 1	
except getopt.GetoptError, v:
	print v
	print_help = 1


if print_help:
	print "Syntax: %s ACTION" % sys.argv[0]
	print "start			start maay [default]"
	print "install_db		install database"
	sys.exit(0)

#sys.argv[0]
#dir = os.path.dirname(sys.argv[0])
#if dir:
#	os.chdir(dir)	

if action == 'start':
	maayMain = maay.maaymain.Maay()
	maayMain.start()
elif action == 'install_db':
	install_db()


