"""
        Constants used in Maay
"""

import maay.datastructure.documentinfo


MAAY_SERVICE_NAME = "Maay"
DBMS_SERVICE_NAME = "Maay MySQL"

HTML_TITLE_PREFIX = "Maay Search"

MAAY_PORT = 6446

# PROTOCOL
MAAY_VERSION = "0.2"
PROTOCOL_VERSION = "0.1"
VENDOR = "maay v0.1"

SEARCH_REQUEST_COMMAND = 0x01
SEARCH_RESPONSE_COMMAND = 0x02
DOWNLOAD_REQUEST_COMMAND = 0x03
DOWNLOAD_RESPONSE_COMMAND = 0x04
PONG_COMMAND = 0x05

HAS_DOCUMENT_CONTENT_FLAG = 1
HAS_DOCUMENT_DESCRIPTION_FLAG = 2

# PRIORITY
LOW_PRIORITY = 0
MEDIUM_PRIORITY = 1
HIGH_PRIORITY = 2

PRIORITY_STR = {LOW_PRIORITY: 'low', MEDIUM_PRIORITY: 'medium', HIGH_PRIORITY: 'high'}

# PROPAGATION PARAMETERS
INIT_TTL = 8
INIT_FNC = 8
INIT_EHC = 10
MIN_SCORE = 0.0

# confidence on value of relevance and popularity
hoeffding_confidence = 0.9

# max number of score per hits
relevant_document_score_count = 5


# SEARCH RANGE
PUBLISHED_SEARCH_RANGE = maay.datastructure.documentinfo.PUBLISHED_STATE
CACHED_SEARCH_RANGE = maay.datastructure.documentinfo.CACHED_STATE
KNOWN_SEARCH_RANGE = maay.datastructure.documentinfo.KNOWN_STATE
PRIVATE_SEARCH_RANGE = maay.datastructure.documentinfo.PRIVATE_STATE
P2P_SEARCH_RANGE = 1 << 6

MAAY_SEARCH_RANGE = PUBLISHED_SEARCH_RANGE | CACHED_SEARCH_RANGE | KNOWN_SEARCH_RANGE | P2P_SEARCH_RANGE

DESKTOP_SEARCH_RANGE = PUBLISHED_SEARCH_RANGE | CACHED_SEARCH_RANGE |PRIVATE_SEARCH_RANGE
INTERNET_SEARCH_RANGE = 1 << 4
INTRANET_SEARCH_RANGE = 1 << 5

ALL_PUBLISHED_SEARCH_RANGE = PUBLISHED_SEARCH_RANGE | CACHED_SEARCH_RANGE | KNOWN_SEARCH_RANGE 
ALL_SEARCH_RANGE = PRIVATE_SEARCH_RANGE | PUBLISHED_SEARCH_RANGE | CACHED_SEARCH_RANGE | KNOWN_SEARCH_RANGE 


# EXCERPT
EXCERPT_SIZE = 80
EXCERPT_HALF_SIZE = EXCERPT_SIZE / 2

MINI_EXCERPT_SIZE = 80
MINI_EXCERPT_HALF_SIZE = MINI_EXCERPT_SIZE / 2

# INDEXATION
MAX_TEXT_CONTENT_STORED_SIZE = 65535
MIN_WORD_SIZE = 2
MAX_WORD_SIZE = 50


# lifetime in second of a result spool. If the search is initiated by
# the local user, the lifetime is infinite
result_spool_lifetime = 40

#
# TASKS PERIODS
#

FLUSH_RESULTS_PERIOD = 2
SCAN_REPOSITORY_PERIOD = 600
AFFINITY_UPDATE_PERIOD = 600
MATCHING_UPDATE_PERIOD = 600
DATABASE_COMMIT_PERIOD = 60
SYSTEM_MONITOR_UPDATE_PERIOD = 1
AGING_PERIOD = 1000

SEARCH_TAB_SIZE = 30

PRIVATE_REPOSITORY_INDEXATION_PERIOD = 3600
PUBLISHED_REPOSITORY_INDEXATION_PERIOD = 3600

change_before_commit = 100

SEARCH_BY_WORD = 0
SEARCH_BY_DOCUMENT_ID = 1

MAX_CONCURRENT_DOWNLOAD = 2

# DEFAULT CONFIGURATION FILE
config_filename = "config/maay.conf"

# SEARCH MODE
NORMAL_SEARCH_MODE = 0
ADVANCED_SEARCH_MODE = 1

# WEIGHT OF ANNOTATION FOR INTENTIONNAL ANNOTATION AND DOWNLOAD
ANNOTATION_SCORE_WEIGHT = 10
DOWNLOAD_SCORE_WEIGHT = 1

# MODE
USER_MODE = 0
DEVELOPPER_MODE = 1

constant_locals = locals()

# TOP MENU ID
SEARCH_MENU_ID = 0
DOCUMENTS_MENU_ID = 1
DOWNLOAD_MENU_ID = 2
NODES_MENU_ID = 3
WORDS_MENU_ID = 4
SYSTEM_MENU_ID = 5
PREFERENCES_MENU_ID = 6
LOGS_MENU_ID = 7
ABOUT_MENU_ID = 8
HELP_MENU_ID = 9

# PREFERENCE MENU ID
SECURITY_PREFERENCE_MENU_ID = 0
INDEXATION_PREFERENCE_MENU_ID = 1
UI_PREFERENCE_MENU_ID = 2
DEBUG_PREFERENCE_MENU_ID = 3

def getValue(var):
    return constant_locals.get(var)

#remove these constants from datastructure.documentinfo
PUBLISHED_STATE = 1 << 0 # 1
CACHED_STATE = 1 << 1 # 2
KNOWN_STATE = 1 << 2 # 4
PRIVATE_STATE = 1 << 3 # 8
UNKNOWN_STATE = 1 << 9 # 


