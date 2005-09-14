import time
from MySQLdb import connect

def main():
    try:
        cnx = connect(db='mysql', host='localhost', user='root')
        cursor = cnx.cursor()
        cursor.execute('SELECT * FROM user;')
        print cursor.fetchall()
    except Exception,exc:
        print exc
    time.sleep(10)
        
if __name__ == '__main__':
    main()
