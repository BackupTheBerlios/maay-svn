""" helper to create the maay mysql instance on windows platform"""
import os

def do_create():
	pipe = os.popen('mysql/bin/mysql.exe -u root mysql', 'w')
	print pipe
	data = file('mysql.sql','rb').read()
	print data
	pipe.write(data)
	pipe.close()
	print 'done'
	
if __name__ == '__main__':
	do_create()
	
	
