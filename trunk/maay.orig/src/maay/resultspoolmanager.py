class ResultSpoolManager:
    def __init__(self):
        self.resultSpoolByQueryID = {}
        self.resultSpools = []
        self.resultSpoolsByNodeID = {}

    def getResultSpoolsByNodeID(self, node_id):
        resultSpools = self.resultSpoolsByNodeID.get(node_id)
        if not resultSpools:
            return []
        return resultSpools

    def insert(self, resultSpool):
        self.resultSpools.append(resultSpool)
        self.resultSpoolByQueryID[resultSpool.getQueryID()] = resultSpool

        node_id = resultSpool.getNodeID()
        resultSpools = self.resultSpoolsByNodeID.get(node_id)
        if not resultSpools:
            self.resultSpoolsByNodeID[node_id] = [resultSpool]
        else:
            resultSpools.append(resultSpool)

#       def createNewResultSpool(self, queryID, query, range, result_count):
#               resultPool = ResultPool(queryID, query, range, result_count)
#               self.resultPools.append(resultPool)
#               self.resultPoolByQueryIDs[queryID] = resultPool

    def getResultSpools(self):
        return self.resultSpools

    def getResultSpool(self, queryID):
        return self.resultSpoolByQueryID.get(queryID)

    def getResultSpoolByIndex(self, index):
        return self.resultPools[index]

    def getResultSpoolIndex(self, resultPool):
        try:
            return self.resultPools.index(resultPool)
        except ValueError:
            return -1

    def getResultSpoolCount(self):
        return len(self.resultPools)

    def closeResultSpool(self, queryID):
        resultPool = self.resultPoolByQueryID[queryID]
        self.resultPools.remove(resultPool)
        del self.resultPoolByQueryID[queryID]

    def removeResultSpool(self, rs):
        del self.resultSpoolByQueryID[rs.getQueryID()]
        self.resultSpoolsByNodeID[rs.getNodeID()].remove(rs)
        self.resultSpools.remove(rs)
        del rs
