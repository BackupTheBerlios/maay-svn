#!/usr/bin/python

""" Main program
"""

import socket
import sys
import getopt
import os.path
import threading
import thread
import logging
import traceback
import cStringIO
import time


import maay.google
import maay.webserver
import maay.core
import maay.constants
import maay.database
import maay.globalvars
import maay.communication
import maay.indexer
import maay.urlindexer
import maay.taskscheduler
import maay.downloadmanager
import maay.potentialnodemanager
import maay.maaywebcache
import maay.tools

import maay.config.configfile
import maay.config.converterfile
import maay.config.templatefile
import maay.config.translationfile
import maay.config.language


if sys.platform == 'win32':
    import maay.win32.win32maaytaskbar
    import maay.win32.win32systemmonitor
    import maay.win32.win32filecrawler
    import maay.win32.win32command
    import maay.win32.win32errorwindow
else:
    import maay.linux.linuxsystemmonitor
    import maay.linux.linuxfilecrawler
    import maay.linux.linuxcommand

class Maay:
    def __init__(self):
        self.__lock = threading.Lock()
        self.__lock.acquire()

    def __forceQuit(self):
        time.sleep(10)
        try:
            maay.globalvars.taskbar.showBalloon("Force quit !")                     
            self.__lock.release()
            maay.globalvars.logger.info("")
            sys.exit(1)
        except:
            pass

    def stop(self, error = 0):
        try:
            print "Stopping Maay, killing me softly ;-) (10 seconds grace)"

            thread.start_new_thread(self.__forceQuit, ())

            maay.globalvars.stop = 1
            if maay.globalvars.indexer:
                if maay.globalvars.indexer.getLastIndexedPrivateFilename():                             
                    maay.globalvars.config.setValue('LastIndexedPrivateFilename', maay.globalvars.indexer.getLastIndexedPrivateFilename())
                maay.globalvars.config.setValue('IndexedDirectory', maay.globalvars.indexer.getIndexedDirectories())
                maay.globalvars.config.setValue('NotIndexedDirectory', maay.globalvars.indexer.getNotIndexedDirectories())
                maay.globalvars.config.setValue('PublishedDirectory', maay.globalvars.indexer.getPublishedDirectories())
                maay.globalvars.config.setValue('NotPublishedDirectory', maay.globalvars.indexer.getNotPublishedDirectories())
                maay.globalvars.config.save()
                
            if maay.globalvars.taskbar:
                maay.globalvars.taskbar.showBalloon("Maay", "Maay is exiting, please wait...")                  
            if maay.globalvars.taskScheduler:
                maay.globalvars.logger.info("Stopping tasks...")
                maay.globalvars.taskScheduler.stop()
            if maay.globalvars.database:
                maay.globalvars.logger.info("Closing database connection...")
                maay.globalvars.database.close()
            if maay.globalvars.taskbar:
                maay.globalvars.logger.info("Closing taskbar...")
                maay.globalvars.taskbar.stop()
                
            if sys.platform == 'win32':
                if error:
                    c = cStringIO.StringIO()
                    ei = sys.exc_info()
                    traceback.print_exception(ei[0], ei[1], ei[2], file=c)
                    #traceback.print_traceback(file=c)
                    errorWindow = maay.win32.win32errorwindow.ErrorWindow(c.getvalue(), os.path.join("logs", "maay.log"))
                    c.close()

                import win32gui
                win32gui.PostQuitMessage(0) # Terminate the app.

            try:
                self.__lock.release()
            except:
                pass

        except:
            maay.globalvars.logger.exception("Error during stop")


    def start(self):
        try:
            import psyco
            print "Psyco module detected ! Use full code optimisation !"
            psyco.full()
        except ImportError:
            print "Psyco module not detected !"

        try:
            import gc
            print "gc module detected !",
            if gc.isenabled():
                print "Automatic garbage collection is enabled."
            else:
                print "Automatic garbage collection is disabled."
        except ImportError:
            print "Psyco module not detected !"


        print_help = 0

        # checking arguments
        try:
            options, arguments = getopt.getopt(sys.argv[1:], 'hc:')
            if len(arguments) != 0:
                print "Syntax error"
                print_help = 1

            config_file = os.path.normpath(maay.constants.config_filename)
            for (option, value) in options:
                if option == '-h':
                    print_help = 1
                elif option == '-c':
                    config_file = value

        except getopt.GetoptError, v:
            print v
            print_help = 1

        if print_help == 1:
            print "Usage: maay.py [OPTIONS]\n"
            print "Options:"
            print "  -c config file (default: config/maay.conf)"
            print "  -h print this help"
            sys.exit()

        maay.globalvars.logger = logging.getLogger('maay')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')                  

        # TODO: close the file_handler properly
        file_handler = logging.FileHandler(os.path.join('logs','maay.log'), 'w')
        file_handler.setFormatter(formatter)
                
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        
        maay.globalvars.logger.addHandler(file_handler)
        maay.globalvars.logger.addHandler(stderr_handler)
        maay.globalvars.logger.setLevel(logging.DEBUG)
        maay.globalvars.logger.info('Creating logger')

        print "Reading config file %s" % config_file
        
        config_variables = {
                                'NodeID' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'Port' : (maay.config.configfile.INT_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'Log' : (maay.config.configfile.CHOICE_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE, ("DEBUG", "INFO", "WARNING", "ERROR", "NOLOG")),
                                'WWWDocumentRoot' : (maay.config.configfile.DIRNAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'LastIndexedPrivateFilename' : (maay.config.configfile.FILENAME_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'PublishedDocumentRoot' : (maay.config.configfile.DIRNAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'CachedDocumentRoot' : (maay.config.configfile.DIRNAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'PrivateDocumentRoot' : (maay.config.configfile.DIRNAME_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'TemporaryDocumentRoot' : (maay.config.configfile.DIRNAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'IndexedDirectory' : (maay.config.configfile.LIST_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'NotIndexedDirectory' : (maay.config.configfile.LIST_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'PublishedDirectory' : (maay.config.configfile.LIST_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'NotPublishedDirectory' : (maay.config.configfile.LIST_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'NeighborList' : (maay.config.configfile.FILENAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'Login' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'Password' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'Template' : (maay.config.configfile.FILENAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'MimeType' : (maay.config.configfile.FILENAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'Accent' : (maay.config.configfile.FILENAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'DatabaseConfig' : (maay.config.configfile.FILENAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'Converter' : (maay.config.configfile.FILENAME_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                                'Language' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'ProxyHost' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'ProxyPort' : (maay.config.configfile.INT_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'ResultPerPage' : (maay.config.configfile.INT_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'RemoteAccess' : (maay.config.configfile.INT_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'LocalAuthentification' : (maay.config.configfile.INT_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'Mode' : (maay.config.configfile.INT_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                                'MaxSimultaneousDownload' : (maay.config.configfile.INT_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE)}

        error = 0

        try:

            maay.globalvars.config = maay.config.configfile.ConfigFile(config_file, config_variables)

            indexed_directories = maay.globalvars.config.getValue("IndexedDirectory") or []
            not_indexed_directories = maay.globalvars.config.getValue("NotIndexedDirectory") or []
            print "not_indexed = %s" % not_indexed_directories
            published_directories = maay.globalvars.config.getValue("PublishedDirectory") or []
            not_published_directories = maay.globalvars.config.getValue("NotPublishedDirectory") or []


            not_configured = False
            
            nodeID = maay.globalvars.config.getValue("NodeID")
            if not nodeID:
                print "Generating node ID"
                nodeID = maay.tools.generate_id()
                maay.globalvars.config.setValue("NodeID", nodeID)
                print "Saving file"
                maay.globalvars.config.save()
                not_configured = True

            private_document_root = maay.globalvars.config.getValue("PrivateDocumentRoot")
            published_document_root = maay.globalvars.config.getValue("PublishedDocumentRoot")
            temporary_document_root = maay.globalvars.config.getValue("TemporaryDocumentRoot")
            cached_document_root = maay.globalvars.config.getValue("CachedDocumentRoot")
            neighbor_list_file = maay.globalvars.config.getValue("NeighborList")
            template_file = maay.globalvars.config.getValue("Template")
            maay.globalvars.result_count_per_page = maay.globalvars.config.getValue("ResultPerPage") or 10
            maay.globalvars.remoteAccess = maay.globalvars.config.getValue("RemoteAccess") or 0
            maay.globalvars.localAuthentification = maay.globalvars.config.getValue("LocalAuthentification") or 0
            maay.globalvars.max_simultaneous_download = maay.globalvars.config.getValue("MaxSimultaneousDownload") or 2

    
            accent_file = maay.globalvars.config.getValue('Accent')
            converter_file = maay.globalvars.config.getValue('Converter')
    #               last_indexed_private_filename = maay.globalvars.config.getValue('LastIndexedPrivateFilename')
            last_indexed_private_filename = None
            last_indexed_published_filename = None
    

            logLevel = maay.globalvars.config.getValue("Log")
            if not logLevel:
                maay.globalvars.logger.setLevel(logging.DEBUG)
            elif logLevel == "DEBUG":
                maay.globalvars.logger.setLevel(logging.DEBUG)
            elif logLevel == "INFO":
                maay.globalvars.logger.setLevel(logging.INFO)
            elif logLevel == "WARNING":
                maay.globalvars.logger.setLevel(logging.WARNING)
            elif logLevel == "ERROR":
                maay.globalvars.logger.setLevel(logging.ERROR)
            elif logLevel == "ERROR":
                maay.globalvars.logger.setLevel(logging.NOLOG)


            database_variables = {
                            'Dbms' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.MANDATORY_VARIABLE),
                            'SQLiteFile' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                            'MySQLHost' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                            'MySQLPort' : (maay.config.configfile.INT_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                            'MySQLUser' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                            'MySQLUnixSocket' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                            'MySQLPassword' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE),
                            'MySQLDatabase' : (maay.config.configfile.STRING_TYPE, maay.config.configfile.OPTIONNAL_VARIABLE)}


            database_config_file = maay.globalvars.config.getValue("DatabaseConfig")

            maay.globalvars.database_config = maay.config.configfile.ConfigFile(database_config_file, database_variables)

            maay.globalvars.login = maay.globalvars.config.getValue("Login")
            maay.globalvars.password = maay.globalvars.config.getValue("Password")

            nodeID = maay.globalvars.config.getValue("NodeID")
            maay.globalvars.port = maay.globalvars.config.getValue("Port")

            maay.globalvars.mode = maay.globalvars.config.getValue("Mode") or maay.constants.USER_MODE


            dbms = maay.globalvars.database_config.getValue('Dbms')

            mysql_host = maay.globalvars.database_config.getValue('MySQLHost')
            mysql_user = maay.globalvars.database_config.getValue('MySQLUser')
            mysql_password = maay.globalvars.database_config.getValue('MySQLPassword')
            mysql_database = maay.globalvars.database_config.getValue('MySQLDatabase')
            mysql_port = maay.globalvars.database_config.getValue('MySQLPort')
            mysql_unix_socket = maay.globalvars.database_config.getValue('MySQLUnixSocket')

            sqlite_file = maay.globalvars.database_config.getValue('SQLiteFile')

            maay.globalvars.accent = maay.config.translationfile.TranslationFile(accent_file)
            maay.globalvars.debug = maay.globalvars.config.getValue('Debug')

            maay.globalvars.logger.info("Creating maay web cache connection on maay.rd.francetelecom.fr")
            maay.globalvars.maayWebCache = maay.maaywebcache.MaayWebCache("maay.rd.francetelecom.fr", 6446)

            maay.globalvars.logger.info("Reading template file %s" % template_file)
            maay.globalvars.templateFile = maay.config.templatefile.TemplateFile(template_file)

            maay.globalvars.logger.info("Reading converter file %s" % converter_file)
            maay.globalvars.converterFile = maay.config.converterfile.ConverterFile(converter_file)

            try:
                hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(socket.gethostname())
                maay.globalvars.ip = ipaddrlist[0]
                maay.globalvars.logger.info("The address of your host is %s" %  maay.globalvars.ip)
                maay.globalvars.logger.info("The name of your host is %s" % hostname)
                maay.globalvars.hostname = hostname
            except:
                # JUST FOR DEBUG: remove this !!!
                maay.globalvars.ip = '127.0.0.1'

            if maay.globalvars.ip == '127.0.0.1':
                maay.globalvars.logger.info("Warning: With this IP, other nodes cannot contact you !")
            numbers = maay.globalvars.ip.split(".")
            if int(numbers[0]) == 10 or (int(numbers[0]) == 172 and 16 <= int(numbers[1]) <= 31) or (int(numbers[0]) == 192 and int(numbers[1] == 168)):
                maay.globalvars.logger.info("Warning: Your host uses a private IP address, only nodes in the intranet can reach you !")

            # Building database connection
            maay.globalvars.logger.info("Creating database manager")
            maay.globalvars.database = maay.database.Database(dbms, host = mysql_host, port = mysql_port, user = mysql_user, passwd = mysql_password, unix_socket = mysql_unix_socket, db = mysql_database, db_file = sqlite_file)

            maay.globalvars.maay_core = maay.core.Core(nodeID, maay.globalvars.ip, maay.globalvars.port)

            maay.globalvars.logger.info('Creating file crawler')

            if sys.platform == 'win32':
                if not_configured:
                    indexed_directories = maay.win32.win32filecrawler.getDefaultIndexableRootDirectories()
                    published_directories = [ os.path.abspath("www/pub") ]

                maay.globalvars.FileCrawlerClass = maay.win32.win32filecrawler.FileCrawler
                maay.globalvars.taskbar = maay.win32.win32maaytaskbar.Win32MaayTaskbar(self)
                maay.globalvars.taskbar.start()
                maay.globalvars.taskbar.showBalloon("Maay", "Maay is starting...")                      

                maay.globalvars.logger.info('Creating Win32 system monitor')

                maay.globalvars.systemMonitor = maay.win32.win32systemmonitor.SystemMonitor()
                maay.globalvars.command = maay.win32.win32command
                maay.win32.win32command.setIdlePriority()
            else:
                if not_configured:
                    indexed_directories = maay.linux.linuxfilecrawler.getDefaultIndexableRootDirectories()
                    published_directories = [ os.path.abspath("www/pub") ]

                maay.globalvars.FileCrawlerClass = maay.linux.linuxfilecrawler.FileCrawler
                maay.globalvars.logger.info('Creating Linux system monitor')
                maay.globalvars.systemMonitor = maay.linux.linuxsystemmonitor.SystemMonitor()
                maay.globalvars.command = maay.linux.linuxcommand

            # Building document indexer
            maay.globalvars.logger.info('Start Indexer')
            maay.globalvars.indexer = maay.indexer.Indexer(indexed_directories, not_indexed_directories, published_directories, not_published_directories, published_document_root, cached_document_root, last_indexed_private_filename, last_indexed_published_filename)
            maay.globalvars.indexer.startIndexCycleProcess()

            # Building URL indexer
            maay.globalvars.logger.info('Start URL Indexer')
            maay.globalvars.urlindexer = maay.urlindexer.URLIndexer(temporary_document_root, cached_document_root)
            maay.globalvars.urlindexer.startIndexCycleProcess()

            # it can be read from an url on the web or given in the maay package
            # TODO: keep it or not: (is obsolete with maaywebcache )
            maay.globalvars.logger.info("Reading neighbor list file %s" % neighbor_list_file)
            maay.globalvars.potentialNodeManager = maay.potentialnodemanager.PotentialNodeManager(neighbor_list_file)

            maay.globalvars.logger.info("Creating Download Manager")
            maay.globalvars.downloadManager = maay.downloadmanager.DownloadManager()
            maay.globalvars.downloadManager.start()

            maay.globalvars.logger.info("Creating communication pool")
            maay.globalvars.communication = maay.communication.Communication(maay.globalvars.maay_core)

            maay.globalvars.logger.info("Reading language file")
            lang = maay.globalvars.config.getValue("Language") or "french"
            maay.globalvars.language = maay.config.language.Language("config/languages/", language = lang)

            maay.globalvars.logger.info("Creating tasks")
            maay.globalvars.taskScheduler = maay.taskscheduler.TaskScheduler()

            maay.globalvars.taskScheduler.add("flush", maay.globalvars.maay_core.flushResults, None, maay.constants.FLUSH_RESULTS_PERIOD)
            maay.globalvars.taskScheduler.add("affinity", maay.globalvars.maay_core.updateAffinity, None, maay.constants.AFFINITY_UPDATE_PERIOD)
#                       maay.globalvars.taskScheduler.add("matching", maay.globalvars.maay_core.updateMatching, maay.globalvars.maay_core.stopUpdateMatching, maay.constants.MATCHING_UPDATE_PERIOD)
            maay.globalvars.taskScheduler.add("published_repository_index", maay.globalvars.indexer.forcePublishedIndexation, None, maay.constants.PUBLISHED_REPOSITORY_INDEXATION_PERIOD)
            maay.globalvars.taskScheduler.add("private_repository_index", maay.globalvars.indexer.forcePrivateIndexation, None, maay.constants.PRIVATE_REPOSITORY_INDEXATION_PERIOD)

            maay.globalvars.taskScheduler.add("system_monitor_update", maay.globalvars.systemMonitor.update, None, maay.constants.SYSTEM_MONITOR_UPDATE_PERIOD)
            maay.globalvars.taskScheduler.add("aging", maay.globalvars.maay_core.executeAging, None, maay.constants.AGING_PERIOD)

            if sys.platform == 'win32':
                maay.globalvars.taskScheduler.add("taskbar_update", maay.globalvars.taskbar.update, None, .1)

            maay.globalvars.taskScheduler.start()

            maay.globalvars.logger.info("Starting web interface on port %d" % maay.globalvars.port)
            maay.webserver.runWebServer(maay.globalvars.port, published_document_root, maay.globalvars.maay_core, maay.globalvars.templateFile)

            maay.globalvars.logger.info("Retrieving servers from maay web cache")
            try:
                server_count = maay.globalvars.maayWebCache.connect(update=1, get=1)
                maay.globalvars.logger.info("maaywebcache: %d servers fetched" % server_count)
            except:
                maay.globalvars.logger.exception("maaywebcache")
            self.__lock.acquire()
            maay.globalvars.logger.info('Exited')
            sys.exit(0)
        except KeyboardInterrupt:
            maay.globalvars.logger.exception("User abort !")
            error = 1                       
        except maay.webserver.WebServerError, e:
            maay.globalvars.logger.exception("Cannot start web server: %s" % e[0])
            error = 1                       
        except:
            maay.globalvars.logger.exception('Unhandled exception')
            error = 1                       
            
        if error == 1:
            try:
                error = 0
                self.stop(error = 1)
            except:
                maay.globalvars.logger.exception('Another unhandled exception')

if __name__ == '__main__':
    m = Maay()
    m.start()
