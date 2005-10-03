""" Handle communication spool to limit simultaneous incoming and outgoing
connection """

# todo:
# manage the spool with semaphors, lock, manage also timeout or failed
# connection and report them by dividing bandwidth by 2
# comment:
#       - ALARM signal do not work on Windows
#       - it is captured in all the threads... (so is useless)

#import connection
import thread
import constants
import globalvars
import signal
import socket
import communication
import httplib
import protocol
import response
import time

MAX_COMMUNICATION_COUNT = 10

#class TimeoutError (Exception): pass
#def SIGALRM_handler(sig, stack): raise TimeoutError()

#signal.signal(signal.SIGALRM, SIGALRM_handler)

class Communication:
    NO_ERROR = 0
    UNREACHABLE_ERROR = 1
    TIMEOUT_ERROR = 2
    CONNECTION_ERROR = 3

    def __init__(self, node):
        self.__node = node

    def __send_search_request_to(self, query_id, TTL, ip, port, search_query, min_score, forwarding_node_count, result_count):
#               signal.alarm(10)
        try:
            connection = httplib.HTTPConnection(ip, port)
            connection.putrequest("POST", "/message")
            connection.endheaders()

            print "send message"

            protocol.sendHeader(connection, constants.SEARCH_REQUEST_COMMAND, query_id, TTL)
            protocol.sendSearchRequest(connection, min_score, forwarding_node_count, result_count, search_query)
            print "get response"
            http_response = connection.getresponse()

            (protocol_version, vendor, node_id, ip, port, bandwidth, counter, command_type, queryID, TTL) = response.readHeader(http_response)

            print "recv pong id = %s %s %s" % (node_id, ip, port)

            last_seen_time = int(time.time())
            nodeInfo = globalvars.maay_core.updateNodeInfo(node_id, ip, port, bandwidth, counter, last_seen_time)
            connection.close()
#               except TimeoutError:
#                       signal.alarm(0)
#                       return communication.Communication.TIMEOUT_ERROR
        except socket.error, (code, message):
            print "Connection problem on node [%s:%s]: %s" % (ip, port, message)
            return communication.Communication.CONNECTION_ERROR

#               signal.alarm(0)

        return communication.Communication.NO_ERROR

    def send_search_request_to(self, query_id, TTL, ip, port, search_query, min_score, forwarding_node_count, result_count):
        print "sending message"
#               thread.start_new_thread(self.__send_search_request_to, (query_id, TTL, nodeInfo, search_query, document_id, min_score, forwarding_node_count, result_count))
        thread.start_new_thread(self.__send_search_request_to, (query_id, TTL, ip, port, search_query, min_score, forwarding_node_count, result_count))
#               self.__send_search_request_to(query_id, TTL, ip, port, search_query, document_id, min_score, forwarding_node_count, result_count)


