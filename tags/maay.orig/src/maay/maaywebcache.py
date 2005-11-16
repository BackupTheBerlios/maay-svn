import httplib

import globalvars

class MaayWebCache:
    def __init__(self, ip, port):
        self.__ip = ip
        self.__port = port

    def connect(self, update=0, get=0):
        connection = httplib.HTTPConnection(self.__ip, self.__port)
        if update == 1:
            url = "/maaywebcache?update=1&id=%s&ip=%s&port=%s" % (globalvars.maay_core.getNodeID(), globalvars.ip, globalvars.port)
            if get == 1:
                url += "&get=1"
        else:
            url = "/maaywebcache" % (globalvars.maay_core.getNodeID(), globalvars.ip, globalvars.port)
            if get == 1:
                url += "?get=1"

        globalvars.logger.debug("attempting to open '%s'" % (url,))
        connection.request("GET", url)

        response = connection.getresponse()
        
        r = response.read()
        servers = r.split("\r\n")
        for s in servers:
            infos = s.split()
            if len(infos) != 3:
                continue
            id = infos[0]
            tcp_addr = infos[1].split(":")
            ip = tcp_addr[0]
            port = tcp_addr[1]
            last_seen_time = int(infos[2])
            
            globalvars.maay_core.updateNodeInfo(id, ip, port, 0, 0, last_seen_time)
        return len(servers)
