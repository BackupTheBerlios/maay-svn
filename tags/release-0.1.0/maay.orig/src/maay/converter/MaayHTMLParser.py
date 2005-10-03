import texttools
import cStringIO

WAITING_INF = 0
WAITING_FIRSTCHAR_ATTNAME = 1
WAITING_NEXTCHAR_ATTNAME = 2
WAITING_NEXT_AFF = 3
WAITING_FIRSTCHAR_VALUE = 4
WAITING_CHAR_IN_QUOTE_VALUE = 5
WAITING_AFTER_QUOTE = 6
WAITING_SPACE_AFTER_AFF = 7
READ_AFF = 8
READ_SUP_END_TAG = 9
READ_INF_END_TAG = 10
WAITING_CHAR_VALUE = 11
WAITING_NEXTCHAR_REM1 = 12
WAITING_NEXTCHAR_REM2 = 13
WAITING_NEXTCHAR_LIGHTREM = 20
WAITING_END_REM1 = 14
WAITING_END_REM2 = 15
WAITING_IN_REM = 16
WAITING_IN_SCRIPT = 17
WAITING_END_SCRIPT1 = 18
WAITING_END_SCRIPT2 = 19

class HTMLParser:

    def __init__(self):
        self.__offset = 0
        self.__pos = 0
        self.__text = cStringIO.StringIO()
        self.__tagName = ""
        self.__tagName = ""
        self.__attName = ""
        self.__attValue = None
        self.__atts = []
        self.__endingTag = 0
        self.__escape = 1
        self.__state = WAITING_INF 
        self.__pos = 0
        self.__offset = 0
        self.__attCount = 0
        self.__pos = -1
        self.__jumpedTag = ""
        self.__lastC = None
        self.__lastLastC = None

    def reset(self):
        self.__init__()

    def handle_starttag(self, tag, attrs):
        pass

    def handle_endtag(self, tag, attrs):
        pass

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_data(self, data):
        pass

    def handle_comment(self, data):
        pass

    def close(self):
        # todo: return datas, likes all the tags finished
        pass

    def getpos(self):
        return self.__pos + self.__offset

    def feed(self, data=None, input=None):
        if data:
            data_length = len(data)
        else:
            data_length = 0
        self.__pos = -1
        while 1:
            self.__pos += 1
            if self.__pos >= data_length:
                break
            if data:
                c = data[self.__pos]
            else:
                c = input.read(1)

#                       print self.__state, c
            # waiting for '<'
            if self.__state == WAITING_INF:
                if c == '<':
                    self.__state = WAITING_FIRSTCHAR_ATTNAME
                else:
                    self.__text.write(c)
            # waiting for tagname
            elif self.__state == WAITING_FIRSTCHAR_ATTNAME:
                if c == '!':
                    self.__state = WAITING_NEXTCHAR_REM1
                elif c == '/':
                    self.handle_data(self.__text.getvalue())
                    self.__text = cStringIO.StringIO()
                    self.__endingTag = 1
                    self.__state = WAITING_NEXTCHAR_ATTNAME
                elif texttools.isAlpha(c):
                    self.__endingTag = 0
                    self.handle_data(self.__text.getvalue())
                    self.__text = cStringIO.StringIO()
                    self.__atts = []
                    self.__attName = c
                    self.__state = WAITING_NEXTCHAR_ATTNAME
                else:
                    self.__text.write("<" + c)

            elif self.__state == WAITING_NEXTCHAR_REM1:
                if c == '-':
                    self.__state = WAITING_NEXTCHAR_REM2
                elif c == '>':
                    self.__state = WAITING_INF
                else:
                    self.__state = WAITING_NEXTCHAR_LIGHTREM

            elif self.__state == WAITING_NEXTCHAR_LIGHTREM:
                if c == '>':
                    self.__state = WAITING_INF

            elif self.__state == WAITING_NEXTCHAR_REM2:
                if c == '-':
                    self.handle_data(self.__text.getvalue())
                    self.__text = cStringIO.StringIO()
                    self.__state = WAITING_IN_REM
                elif c == '>':
                    self.__state = WAITING_INF

            elif self.__state == WAITING_IN_REM:
                if c == '-':
                    self.__state = WAITING_END_REM1
                else:
                    self.__text.write(c)

            elif self.__state == WAITING_END_REM1:
                if c == '-':
                    self.__state = WAITING_END_REM2
                else:
                    self.__text.write("-" + c)
                    self.__state = WAITING_IN_REM


            elif self.__state == WAITING_END_REM2:
                if c == '>':
                    self.handle_comment(self.__text.getvalue())
                    self.__text = cStringIO.StringIO()                                      
                    self.__state = WAITING_INF
                else:
                    self.__text.write("--" + c)
                    self.__state = WAITING_IN_REM

            elif self.__state == WAITING_NEXTCHAR_ATTNAME:
                if texttools.isAlphaNum(c):
                    self.__attName += c
                elif texttools.isSpace(c):
                    self.__state = WAITING_NEXT_AFF
                elif c == '=':
                    self.__state = WAITING_FIRSTCHAR_VALUE
                elif c == '<':
                    self.__state = READ_INF_END_TAG
                elif c == '>':
                    self.__state = READ_SUP_END_TAG

            elif self.__state == WAITING_NEXT_AFF:
                if texttools.isSpace(c):
                    pass
                elif c == '>':
                    self.__state = READ_SUP_END_TAG
                else: 
                    if self.__attName:
                        self.__atts.append((self.__attName, self.__attValue))
                        self.__attName = c
                        self.__attValue = None
                        self.__attCount += 1
                    self.__state = WAITING_NEXTCHAR_ATTNAME

            elif self.__state == WAITING_FIRSTCHAR_VALUE:
                if texttools.isSpace(c):
                    pass
                elif c in ("\"", "'"):
                    self.__quote = c
                    self.__attValue = ""
                    self.__state = WAITING_CHAR_IN_QUOTE_VALUE
                elif c == '<':
#                                       self.__state = READ_END_TAG
# to verify...
                    self.__state = READ_INF_END_TAG
                else:
                    if not self.__attValue:
                        self.__attValue = c
                    else:
                        self.__attValue += c
                    self.__state = WAITING_CHAR_VALUE

            elif self.__state == WAITING_CHAR_VALUE:
                if texttools.isSpace(c):
                    self.__atts.append((self.__attName, self.__attValue))
                    self.__attName = ""
                    self.__attValue = None
                    self.__state = WAITING_NEXTCHAR_ATTNAME
                elif c == '>':
                    self.__state = READ_SUP_END_TAG
                else:
                    if not self.__attValue:
                        self.__attValue = c
                    else:
                        self.__attValue += c


            elif self.__state == WAITING_CHAR_IN_QUOTE_VALUE:
                if c == self.__quote:
                    self.__state = WAITING_AFTER_QUOTE
                else:
                    if not self.__attValue:
                        self.__attValue = c
                    else:
                        self.__attValue += c

            elif self.__state == WAITING_AFTER_QUOTE:
                if texttools.isSpace(c):
                    self.__state = WAITING_SPACE_AFTER_AFF
                elif c == '<':
                    self.__state = READ_INF_END_TAG
                elif c == '>':
                    self.__state = READ_SUP_END_TAG

            elif self.__state == WAITING_SPACE_AFTER_AFF:
                if texttools.isSpace(c):
                    pass
                elif c == '<':
                    self.__state = READ_INF_END_TAG
                elif c == '>':
                    self.__state = READ_SUP_END_TAG
                else:
                    self.__atts.append((self.__attName, self.__attValue))
                    self.__attName = c
                    self.__attValue = None
                    self.__state = WAITING_NEXTCHAR_ATTNAME



            elif self.__state == WAITING_IN_SCRIPT:
                if c == '<':
                    self.__state = WAITING_END_SCRIPT1
                else:
                    self.__text.write(c)

            elif self.__state == WAITING_END_SCRIPT1:
                if c == '/':
                    self.__attName = ""
                    self.__endingTag = 1
                    self.__state = WAITING_END_SCRIPT2
                else:
                    self.__state = WAITING_IN_SCRIPT
                    self.__text.write("<" + c)

            elif self.__state == WAITING_END_SCRIPT2:
                if texttools.isAlpha(c):
                    self.__attName += c
                elif c == '>':
#                                       print self.__attName
                    if self.__attName.lower() == self.__jumpedTag:
                        self.handle_data(self.__text.getvalue())
                        self.__text = cStringIO.StringIO()                                              
                        self.__state = READ_SUP_END_TAG
                    else:
                        self.__state = WAITING_IN_SCRIPT
                        self.__text.write("</" + self.__attName + c)
                else:
                    self.__text.write("</" + self.__attName + c)
                    self.__state = WAITING_IN_SCRIPT

#                       if self.__state == READ_AFF:
#                               if self.__attName:
#                                       self.__atts.append((self.__attName, self.__attValue))
#                                       self.__attName = ""
#                               self.__state = WAITING_INF

            if self.__state == READ_SUP_END_TAG:
                if self.__attName:
                    if self.__lastC == '/' and self.__lastLastC == ' ':
                        self.handle_startendtag(self.__atts[0][0], self.__atts[1:])
                        self.__state = WAITING_INF
                    else:
                        self.__atts.append((self.__attName, self.__attValue))
                        self.__state = WAITING_INF

                        if self.__endingTag:
                            self.handle_endtag(self.__atts[0][0], self.__atts[1:])
                            self.__state = WAITING_INF
                        else:
                            self.handle_starttag(self.__atts[0][0], self.__atts[1:])
                            if self.__atts[0][0].lower() in ('script', 'style'):
                                self.__state = WAITING_IN_SCRIPT
                                self.__jumpedTag = self.__atts[0][0].lower()
                            else:
                                self.__state = WAITING_INF

                self.__attName = ""
                self.__attValue = None

                self.__atts = []

            if self.__state == READ_INF_END_TAG:
                if self.__attName:
                    self.__atts.append((self.__attName, self.__attValue))
                    self.__attName = ""
                self.__state = WAITING_FIRSTCHAR_ATTNAME

            self.__lastLastC = self.__lastC
            self.__lastC = c


        self.__offset += self.__pos

