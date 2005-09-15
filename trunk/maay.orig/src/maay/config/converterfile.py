""" This module read a file describing the conversion between special characters(accent, copyright symbol, ...) to others characters
"""

import re

class Converter:
    def __init__(self, src_mime_type, dst_type, command):
        self.src_mime_type = src_mime_type
        self.dst_type = dst_type
        self.command = command

class ConverterFile:

    def __init__(self, conversion_file):
        self.__converters = {}

        fd = file(conversion_file, 'r')
        line_number = 0
        while 1:
            line_number += 1
            line = fd.readline()
            if line == '':
                break
            words = line.split(None, 2)

            if len(words) == 0:
                continue
            if words[0][0] == '#':
                continue

            if len(words) != 3:
                print "Error in file %s line %d: %s" % (conversion_file, line_number, line)
                print "expect [source mime_type] [destination type]" 
                continue

            src_mime_type = words[0]
            dst_type = words[1]
            command = words[2].rstrip()

            if not dst_type in ('html', 'text'):
                print "Error in file %s line %d: %s" % (conversion_file, line_number, line)
                print "destination type should be 'html' or 'text'"
                continue
                
            if self.__converters.has_key(src_mime_type):
                print "Error in file %s line %d: %s" % (conversion_file, line_number, line)
                print "converter for source mime type %s is already defined" % (src_mime_type)
                continue

            self.__converters[src_mime_type] = Converter(src_mime_type, dst_type, command)

        # add src_mime_type html and text
        if not self.__converters.has_key("text/html"):
            self.__converters["text/html"] = Converter("text/html", "html", 'None')
        if not self.__converters.has_key("text/plain"):
            self.__converters["text/plain"] = Converter("text/plain", "text", 'None')

    def get_converter(self, src_mime_type):
        return self.__converters.get(src_mime_type)

#cfile = ConversionFile("config/converter.conf")
#c = cfile.get_converter('application/pdf')
#print "c.converter = %s" % c.command

