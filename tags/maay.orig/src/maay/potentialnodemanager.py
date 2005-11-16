import globalvars

class NodeTCPInfo:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

class PotentialNodeManager:

    def __init__(self, filename = None):
        self.__nodeTCPInfos = []
        self.__nodeTCPInfosHT = {}
        if filename:
            self.readFile(filename)

    def readFile(self, filename):
        fd = file(filename, 'r')
        while 1:
            line = fd.readline()
            if not line or line == "":
                break
            words = line.split()
    
            ip, port = words
    
            nodeInfos = globalvars.database.getNodeInfos(ip=ip, port=port)
            if nodeInfos:
                continue

            nodeTCPInfo = NodeTCPInfo(ip, port)
            self.__nodeTCPInfos.append(nodeTCPInfo)
            self.__nodeTCPInfosHT[(ip,port)] = nodeTCPInfo

    def removeNodeTCPInfo(self, ip, port):
        nodeTCPInfo = self.__nodeTCPInfosHT.get((ip,port))
        if nodeTCPInfo:
            del self.__nodeTCPInfosHT[(ip,port)]
            self.__nodeTCPInfos.remove(nodeTCPInfo)

    def pop(self):
        if len(self.__nodeTCPInfos) == 0:
            return None
        nodeTCPInfo = self.__nodeTCPInfos.pop()
        del self.__nodeTCPInfosHT[(nodeTCPInfo.ip,nodeTCPInfo.port)]
        return nodeTCPInfo

