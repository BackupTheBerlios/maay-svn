"""
  Miscelaneous functions.
"""

import sha
import time

def size_str(s):
    if s < 1024:
        return "%d bytes" % s 
    elif s < 1048576:
        return "%.1f k" % (float(s) / 1024)
    else:
        return "%.1f M" % (float(s) / 1048576)

def date_str(t):
    return time.strftime("%d %b %Y", time.localtime(t))

def long_date_str(t):
    return time.strftime("%d %b %Y %H:%M:%S", time.localtime(t))


def maay_hash(s):
#       return sha.sha(s).hexdigest()
    return sha.sha(s).hexdigest()

def generate_id():
    return maay_hash(str(time.time()))

def query_str(search_query):
    s = ""
    for w in search_query:
        s += w + " "
    return s.rstrip(" ")

def seq2lines(seq):
    r = ""
    if not seq:
        return r
        
    for s in seq:
        r += s + "\r\n"
    return r
    
def remove_void_entries(seq):
    for i in xrange(len(seq) - 1, 0, -1):
        seq[i] = seq[i].strip()
        if not seq[i]:
            del seq[i]
            
def file2stream(f):
    return Output(f)

class Output:
    def __init__(self, output):
        self.__output = output

    def send(self, size = None):
        self.__output.write(size)
