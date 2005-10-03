import maay.constants
import maay.templatetools

#
# Here goes all the global variables
#

potentialNodes = []

taskScheduler = None

logger = None
database = None
indexer = None
maay_core = None
templateFile = None
config = None
communication = None
downloadManager = None
converterFile = None
ip = None
nodeID = None
hostname = None
port = None
debug = 0
potentialNodeManager = None
login = None
password = None
urlindexer = None
search_mode = maay.constants.NORMAL_SEARCH_MODE
systemMonitor = None
privateFileCrawler = None
publishedFileCrawler = None

stop = 0
language = None
taskbar = None
command = None
sessionID = None

remoteAccess = None
localAuthentification = None

max_simultaneous_download = None

mode = maay.constants.USER_MODE

result_count_per_page = 10

def _(x):
    return x

constants = maay.constants

templatetools = maay.templatetools
