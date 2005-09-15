""" This module read a file describing the conversion between special characters(accent, copyright symbol, ...) to others characters
"""

import re

class TranslationFile:

    def __init__(self, translation_file):
        print "Reading accent file %s" % translation_file
        fd = file(translation_file, 'r')
        self.__destinationChar = {}
        self.__sourceChars = {}
        self.__regularExpression = ""
        self.__inverseRegularExpression = ""
        while 1:
            line = fd.readline()
            if line == '':
                break
            words = line.split()

            if len(words) == 0:
                continue

            if words[0][0] == '#':
                continue

            dest_char = words[0]

            self.__sourceChars[dest_char] = []
            for src_char in words[1:]:
                if src_char[0] == '#':
                    break
                self.__destinationChar[src_char] = dest_char
                self.__sourceChars[dest_char].append(src_char)
                self.__regularExpression += "|%s" % src_char
                self.__inverseRegularExpression += "|%s" % dest_char
        fd.close()
        self.__regularExpression = self.__regularExpression.strip('|')
        self.__inverseRegularExpression = self.__inverseRegularExpression.strip('|')

    def getDestinationChar(self, char):
        return self.__destinationChar(char)

    def getSourceChar(self, char):
        return self.__sourceChars.get(char)

    def getRegularExpression(self):
        return self.__regularExpression
        
    def __translate(self, matchobj):
        return self.__destinationChar[matchobj.group(0)]
        
    def translate(self, data):
        return re.sub(self.__regularExpression, self.__translate, data)

    def __extendsMatchingPattern(self, matchobj):
        # todo : to optimize by precalculating string
        char = matchobj.group(0)

        sourceLowerChar = self.__sourceChars.get(char.lower())
        if not sourceLowerChar:
            sourceLowerChar = []
        sourceUpperChar = self.__sourceChars.get(char.upper())
        if not sourceUpperChar:
            sourceUpperChar = []

        r = "(%s|%s" % (char.lower(), char.upper())

        for s in sourceLowerChar + sourceUpperChar:
            r += "|%s" % s
        r += ")"
        return r

    def extendsMatchingPattern(self, pattern):
#               return re.sub(self.__inverseRegularExpression, self.__extendsMatchingPattern, pattern)
        return re.sub("[a-zA-Z0-9]|%s" % self.__inverseRegularExpression, self.__extendsMatchingPattern, pattern)
