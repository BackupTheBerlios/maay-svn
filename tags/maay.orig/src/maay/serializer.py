import struct

#def dump(className, object, vars):
#       resultDict = {}
#       for (var, type) in vars.items():
#               resultDict[var] = getattr(object, "_%s__%s" % (className, var))
#       return resultDict
                                                                                                                                                                
#def load(self, vars):
#       pass

# sequences = [ ('i', 4), ('s', 15), ('v', 2) ]

def read_string(input, size):
    return input.read(size)

# string limited to 255 chars
def read_vstring(input):
    l = ord(input.read(1))
    return input.read(l)

def read_integer(input):
    return struct.unpack("I", input.read(4))[0] - 1

def read_float(input):
    return struct.unpack("f", input.read(4))[0]

def read_short(input):
    return struct.unpack("H", input.read(2))[0]

def read_char(input):
    return struct.unpack("B", input.read(1))[0]

def read_ip(input):
    b = struct.unpack("4B", input.read(4))
    return "%d.%d.%d.%d" % b

def send_string(output, v, size):
    output.send(struct.pack("%ds" % size, v))

# string limited to 255 chars
def send_vstring(output, v):
    output.send(struct.pack("B", len(v)))
    output.send(v)

def send_integer(output, v):
    output.send(struct.pack("I", v + 1))

def send_float(output, v):
    output.send(struct.pack("f", v))
    
def send_char(output, v):
    output.send(struct.pack("B", v))
    
def send_short(output, v):
    output.send(struct.pack("H", v))

def send_ip(output, v):
    p = v.split(".")
    output.send(struct.pack("4B", int(p[0]), int(p[1]), int(p[2]), int(p[3])))
    
#def str2int

header_type = (
                        ('s', 4),               # Protocol version ASCII String [4]
                        ('s', 16),              # Vendor ASCII String [16]
                        ('s', 20),              # Sender node ID [20]
                        ('n',),                 # Sender node IP [4]
                        ('h', None),    # Sender node Port [2]
                        ('c', None),    # Bandwidth [1]
                        ('s', 20),              # Query ID [20]
                        ('c', None),    # Command Type [1]
                        ('c', None)             # Time-To-Live (TTL) [1]
                )

def read(fd, types):
    results = []
    for type, size in types:
        if type == 'i':
            results.append(read_integer(fd))
        elif type == 'c':
            results.append(read_char(fd))
        if type == 's':
            results.append(read_string(fd, size))
        if type == 'v':
            results.append(read_vstring(fd))
    return results

#def write(fd, types, values):
#       i = 0
#       for type, size in types:
#               value = values[i]
#               if type == 'i':
#                       write_integer(value)
#               if type == 's':
#                       write_string(value, size)
#               if type == 'v':
#                       write_vstring(value)
#               i += 1
