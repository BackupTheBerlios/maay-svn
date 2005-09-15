import re
import texttools
import cStringIO

def textToText(buffer):
    # extract the title (first lines beforce void carriage return)
    #get title
    title = ""

#       start = 0
#       iter = re.finditer('\n', buffer)
#       while 1:
#               try:
#                       match = iter.next()
#               except StopIteration:
#                       break
#       
#               line = buffer[start:match.start()]
#               start = match.start() + 1
#               line = line.rstrip()
#               line = line.lstrip()
#               if line != '':
#                       title = line
#
    # contraction of the content of the buffer
    contractedText = cStringIO.StringIO()
    iter = re.finditer('\w+', buffer)
    bufferLength = len(buffer)
    pos = -1
    space = 1
    while 1:
        pos += 1
        if pos >= bufferLength:
            break

        c = buffer[pos]
        if ord(c) < 32:
            c = ' '
        if texttools.isSpace(c):
            if space == 0:
                contractedText.write(' ')
            space = 1
        else:
            contractedText.write(c)
            space = 0
    text = contractedText.getvalue()
    title = text[0:60]
    return (title, text)
    
