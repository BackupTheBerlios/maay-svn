class NodeInfo:
    # should we send also relevance and popularity of node to others with
    # the results ?
    def __init__(self, node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.counter = counter
        self.last_seen_time = last_seen_time
        self.claim_count = claim_count
        self.affinity = affinity
        self.bandwidth = bandwidth
