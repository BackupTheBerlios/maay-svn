import cgi
import urlparse
import time

import globalvars

def handle_get(httpRequestHandler):
    u = urlparse.urlparse(httpRequestHandler.path)

    args = cgi.parse_qs(u[4])
    q = args.get('q')

    updates = args.get("update")
    if updates and updates[0] == "1":
        update = 1
    else:
        update = 0

    gets = args.get("get")
    if gets and gets[0] == "1":
        get = 1
    else:
        get = 0

    ips = args.get("ip")
    if ips:
        ip = ips[0]
    else:
        ip = None

    ids = args.get("id")
    if ids:
        id = ids[0]
    else:
        id = None

    ports = args.get("port")
    if ports:
        port = ports[0]
    else:
        port = None

    print "update %s:%s (%s)" % (ip, port, id)
    if update and id and ip and port:
        globalvars.maay_core.updateNodeInfo(id, ip, int(port), 0, 0, time.time())

    if get:
        httpRequestHandler.send_response(200)
        httpRequestHandler.send_header('Content-Type', "text/plain")
        httpRequestHandler.send_header('Connection', 'close')
        httpRequestHandler.end_headers()

        nodeInfos = globalvars.database.getNodeInfos()

        for nodeInfo in nodeInfos:
            httpRequestHandler.wfile.write("%s %s:%s %s\r\n" % (nodeInfo.node_id, nodeInfo.ip, nodeInfo.port, nodeInfo.last_seen_time))
