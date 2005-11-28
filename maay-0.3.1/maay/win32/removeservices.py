#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This program is free software; you can redistribute it and/or modify it
#     under the terms of the GNU General Public License as published by the
#     Free Software Foundation; either version 2 of the License, or (at your
#     option) any later version.
#     
#     This program is distributed in the hope that it will be useful, but
#     WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
#     Public License for more details.
#     
#     You should have received a copy of the GNU General Public License along
#     with this program; if not, write to the Free Software Foundation, Inc.,
#     59 Temple Place - Suite 330, Boston, MA 02111-1307 USA.
#     

""" stop and remove mysql and maay services on windows platform"""

__revision__ = '$Id: removeservices.py 632 2005-11-23 17:13:51Z dnf $'

import win32serviceutil
import win32service
import time

def removeService(service_name):
       # dirty remove of service
       try:
           status = win32serviceutil.QueryServiceStatus(service_name)[0]
           print "Service '%s' is installed !" % service_name

	   print "status = %s" % status

           if status & win32service.SERVICE_START:
               try:
                   print "Stop service '%s'" % service_name
                   win32serviceutil.StopService(service_name)
               except:
                   pass
           try:
               print "Remove service '%s'" % service_name
               win32serviceutil.RemoveService(service_name)
           except Exception, e:
               pass

           print "Waiting service to be removed..."
           while not status & win32service.SERVICE_STOP :
	       print status
               try:
                   status = win32serviceutil.QueryServiceStatus(service_name)[0]
               except:
                   break
               time.sleep(1)
       except:
           print "Service '%s' not installed !" % service_name

removeService("Maay")
removeService("MySQL")
