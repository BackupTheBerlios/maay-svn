import re
import cStringIO

asciiToHtmlCodes = {
                "": "",
                "\"": "&quot;",
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                "?": "&trade;",
                " ": "&nbsp;",
                "�": "&iexcl;",
                "�": "&cent;",
                "�": "&pound;",
                "�": "&curren;",
                "�": "&yen;",
                "�": "&brvbar;",
                "�": "&sect;",
                "�": "&uml;",
                "�": "&copy;",
                "�": "&ordf;",
                "�": "&laquo;",
                "�": "&not;",
                "�": "&shy;",
                "�": "&reg;",
                "�": "&macr;",
                "�": "&deg;",
                "�": "&plusmn;",
                "�": "&sup2;",
                "�": "&sup3;",
                "�": "&acute;",
                "�": "&micro;",
                "�": "&para;",
                "�": "&middot;",
                "�": "&cedil;",
                "�": "&sup1;",
                "�": "&ordm;",
                "�": "&raquo;",
                "�": "&frac14;",
                "�": "&frac12;",
                "�": "&frac34;",
                "�": "&iquest;",
                "�": "&Agrave;",
                "�": "&Aacute;",
                "�": "&Acirc;",
                "�": "&Atilde;",
                "�": "&Auml;",
                "�": "&Aring;",
                "�": "&AElig;",
                "�": "&Ccedil;",
                "�": "&Egrave;",
                "�": "&Eacute;",
                "�": "&Ecirc;",
                "�": "&Euml;",
                "�": "&Igrave;",
                "�": "&Iacute;",
                "�": "&Icirc;",
                "�": "&Iuml;",
                "�": "&eth;",
                "�": "&Ntilde;",
                "�": "&Ograve;",
                "�": "&Oacute;",
                "�": "&Ocirc;",
                "�": "&Otilde;",
                "�": "&Ouml;",
                "�": "&times;",
                "�": "&Oslash;",
                "�": "&Ugrave;",
                "�": "&Uacute;",
                "�": "&Ucirc;",
                "�": "&Uuml;",
                "�": "&Yacute;",
                "�": "&thorn;",
                "�": "&szlig;",
                "�": "&agrave;",
                "�": "&aacute;",
                "�": "&acirc;",
                "�": "&atilde;",
                "�": "&auml;",
                "�": "&aring;",
                "�": "&aelig;",
                "�": "&ccedil;",
                "�": "&egrave;",
                "�": "&eacute;",
                "�": "&ecirc;",
                "�": "&euml;",
                "�": "&igrave;",
                "�": "&iacute;",
                "�": "&icirc;",
                "�": "&iuml;",
                "�": "&eth;",
                "�": "&ntilde;",
                "�": "&ograve;",
                "�": "&oacute;",
                "�": "&ocirc;",
                "�": "&otilde;",
                "�": "&ouml;",
                "�": "&divide;",
                "�": "&oslash;",
                "�": "&ugrave;",
                "�": "&uacute;",
                "�": "&ucirc;",
                "�": "&uuml;",
                "�": "&yacute;",
                "�": "&thorn;",
                "�": "&yuml;"
}

htmlToAsciiCodes= {
                "": "",
                "&quot;": "\"",
                "&amp;": "&",
                "&lt;": "<",
                "&gt;": ">",
                "&trade;": "?",
                "&nbsp;": " ",
                "&iexcl;": "�",
                "&cent;": "�",
                "&pound;": "�",
                "&curren;": "�",
                "&yen;": "�",
                "&brvbar;": "�",
                "&sect;": "�",
                "&uml;": "�",
                "&copy;": "�",
                "&ordf;": "�",
                "&laquo;": "�",
                "&not;": "�",
                "&shy;": "�",
                "&reg;": "�",
                "&macr;": "�",
                "&deg;": "�",
                "&plusmn;": "�",
                "&sup2;": "�",
                "&sup3;": "�",
                "&acute;": "�",
                "&micro;": "�",
                "&para;": "�",
                "&middot;": "�",
                "&cedil;": "�",
                "&sup1;": "�",
                "&ordm;": "�",
                "&raquo;": "�",
                "&frac14;": "�",
                "&frac12;": "�",
                "&frac34;": "�",
                "&iquest;": "�",
                "&Agrave;": "�",
                "&Aacute;": "�",
                "&Acirc;": "�",
                "&Atilde;": "�",
                "&Auml;": "�",
                "&Aring;": "�",
                "&AElig;": "�",
                "&Ccedil;": "�",
                "&Egrave;": "�",
                "&Eacute;": "�",
                "&Ecirc;": "�",
                "&Euml;": "�",
                "&Igrave;": "�",
                "&Iacute;": "�",
                "&Icirc;": "�",
                "&Iuml;": "�",
                "&eth;": "�",
                "&Ntilde;": "�",
                "&Ograve;": "�",
                "&Oacute;": "�",
                "&Ocirc;": "�",
                "&Otilde;": "�",
                "&Ouml;": "�",
                "&times;": "�",
                "&Oslash;": "�",
                "&Ugrave;": "�",
                "&Uacute;": "�",
                "&Ucirc;": "�",
                "&Uuml;": "�",
                "&Yacute;": "�",
                "&thorn;": "�",
                "&szlig;": "�",
                "&agrave;": "�",
                "&aacute;": "�",
                "&acirc;": "�",
                "&atilde;": "�",
                "&auml;": "�",
                "&aring;": "�",
                "&aelig;": "�",
                "&ccedil;": "�",
                "&egrave;": "�",
                "&eacute;": "�",
                "&ecirc;": "�",
                "&euml;": "�",
                "&igrave;": "�",
                "&iacute;": "�",
                "&icirc;": "�",
                "&iuml;": "�",
                "&eth;": "�",
                "&ntilde;": "�",
                "&ograve;": "�",
                "&oacute;": "�",
                "&ocirc;": "�",
                "&otilde;": "�",
                "&ouml;": "�",
                "&divide;": "�",
                "&oslash;": "�",
                "&ugrave;": "�",
                "&uacute;": "�",
                "&ucirc;": "�",
                "&uuml;": "�",
                "&yacute;": "�",
                "&thorn;": "�",
                "&yuml;": "�",
        }



def asciiToHtml(text):
    start = 0
    # I don't know if it worth to do all the replacements from the table above
    convertedText = re.sub('<', '&lt;', text)
    convertedText = re.sub('>', '&gt;', convertedText)
    return convertedText
#       while 1:
#               try:
#                       match = iter.next()
#               except StopIteration:
#                       break
#               
#               c = text[


def htmlToText(text):
    start = 0
    convertedText = cStringIO.StringIO()
    iter = re.finditer('&[a-zA-Z]+|&#\[0-9]+;;', text)

    while 1:
        try:
            match = iter.next()
        except StopIteration:
            break
            
        space = 0
        convertedText.write(text[start:match.start()])

        # match.string and text[match.start():match.end()+1] are not equivalent !
        str = text[match.start():match.end()+1]

        if str[1] == '#':
            number = str[2:len(str) - 1]
            try:
                nb = int(number)
                if 32 <= nb < 255:
                    convertedText += chr(nb)
                else:
                    space = 1
            except:
                convertedText.write(number)
                
        elif htmlToAsciiCodes.has_key(str):
            if str == "&nbsp;":
                space = 1
            else:
                convertedText.write(htmlToAsciiCodes[str])
        else:
            convertedText.write(str)

        start = match.end()
        if space == 1:
            while start < len(text) - 1 and text[start] == ' ':
                start += 1

    convertedText.write(text[start:])
    return convertedText.getvalue()

def __htmlToTextRepl(match):

    str = match.string
    if str[1] == '#':
        number = str[2:len(str) - 1]
        nb = int(number)
        if 32 <= nb < 255:
            return chr(nb)
    elif htmlToAsciiCodes.has_key(str):
        if str != "&nbsp;":
            return htmlToAsciiCodes[str]
    else:
        convertedText += str

def htmlToText2(text):
    return re.sub('&\w+;|&#\d+;', __htmlToTextRepl, text)
