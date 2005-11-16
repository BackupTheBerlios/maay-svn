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
                "¡": "&iexcl;",
                "¢": "&cent;",
                "£": "&pound;",
                "¤": "&curren;",
                "¥": "&yen;",
                "¦": "&brvbar;",
                "§": "&sect;",
                "¨": "&uml;",
                "©": "&copy;",
                "ª": "&ordf;",
                "«": "&laquo;",
                "¬": "&not;",
                "­": "&shy;",
                "®": "&reg;",
                "¯": "&macr;",
                "°": "&deg;",
                "±": "&plusmn;",
                "²": "&sup2;",
                "³": "&sup3;",
                "´": "&acute;",
                "µ": "&micro;",
                "¶": "&para;",
                "·": "&middot;",
                "¸": "&cedil;",
                "¹": "&sup1;",
                "º": "&ordm;",
                "»": "&raquo;",
                "¼": "&frac14;",
                "½": "&frac12;",
                "¾": "&frac34;",
                "¿": "&iquest;",
                "À": "&Agrave;",
                "Á": "&Aacute;",
                "Â": "&Acirc;",
                "Ã": "&Atilde;",
                "Ä": "&Auml;",
                "Å": "&Aring;",
                "Æ": "&AElig;",
                "Ç": "&Ccedil;",
                "È": "&Egrave;",
                "É": "&Eacute;",
                "Ê": "&Ecirc;",
                "Ë": "&Euml;",
                "Ì": "&Igrave;",
                "Í": "&Iacute;",
                "Î": "&Icirc;",
                "Ï": "&Iuml;",
                "Ð": "&eth;",
                "Ñ": "&Ntilde;",
                "Ò": "&Ograve;",
                "Ó": "&Oacute;",
                "Ô": "&Ocirc;",
                "Õ": "&Otilde;",
                "Ö": "&Ouml;",
                "×": "&times;",
                "Ø": "&Oslash;",
                "Ù": "&Ugrave;",
                "Ú": "&Uacute;",
                "Û": "&Ucirc;",
                "Ü": "&Uuml;",
                "Ý": "&Yacute;",
                "Þ": "&thorn;",
                "ß": "&szlig;",
                "à": "&agrave;",
                "á": "&aacute;",
                "â": "&acirc;",
                "ã": "&atilde;",
                "ä": "&auml;",
                "å": "&aring;",
                "æ": "&aelig;",
                "ç": "&ccedil;",
                "è": "&egrave;",
                "é": "&eacute;",
                "ê": "&ecirc;",
                "ë": "&euml;",
                "ì": "&igrave;",
                "í": "&iacute;",
                "î": "&icirc;",
                "ï": "&iuml;",
                "ð": "&eth;",
                "ñ": "&ntilde;",
                "ò": "&ograve;",
                "ó": "&oacute;",
                "ô": "&ocirc;",
                "õ": "&otilde;",
                "ö": "&ouml;",
                "÷": "&divide;",
                "ø": "&oslash;",
                "ù": "&ugrave;",
                "ú": "&uacute;",
                "û": "&ucirc;",
                "ü": "&uuml;",
                "ý": "&yacute;",
                "þ": "&thorn;",
                "ÿ": "&yuml;"
}

htmlToAsciiCodes= {
                "": "",
                "&quot;": "\"",
                "&amp;": "&",
                "&lt;": "<",
                "&gt;": ">",
                "&trade;": "?",
                "&nbsp;": " ",
                "&iexcl;": "¡",
                "&cent;": "¢",
                "&pound;": "£",
                "&curren;": "¤",
                "&yen;": "¥",
                "&brvbar;": "¦",
                "&sect;": "§",
                "&uml;": "¨",
                "&copy;": "©",
                "&ordf;": "ª",
                "&laquo;": "«",
                "&not;": "¬",
                "&shy;": "­",
                "&reg;": "®",
                "&macr;": "¯",
                "&deg;": "°",
                "&plusmn;": "±",
                "&sup2;": "²",
                "&sup3;": "³",
                "&acute;": "´",
                "&micro;": "µ",
                "&para;": "¶",
                "&middot;": "·",
                "&cedil;": "¸",
                "&sup1;": "¹",
                "&ordm;": "º",
                "&raquo;": "»",
                "&frac14;": "¼",
                "&frac12;": "½",
                "&frac34;": "¾",
                "&iquest;": "¿",
                "&Agrave;": "À",
                "&Aacute;": "Á",
                "&Acirc;": "Â",
                "&Atilde;": "Ã",
                "&Auml;": "Ä",
                "&Aring;": "Å",
                "&AElig;": "Æ",
                "&Ccedil;": "Ç",
                "&Egrave;": "È",
                "&Eacute;": "É",
                "&Ecirc;": "Ê",
                "&Euml;": "Ë",
                "&Igrave;": "Ì",
                "&Iacute;": "Í",
                "&Icirc;": "Î",
                "&Iuml;": "Ï",
                "&eth;": "Ð",
                "&Ntilde;": "Ñ",
                "&Ograve;": "Ò",
                "&Oacute;": "Ó",
                "&Ocirc;": "Ô",
                "&Otilde;": "Õ",
                "&Ouml;": "Ö",
                "&times;": "×",
                "&Oslash;": "Ø",
                "&Ugrave;": "Ù",
                "&Uacute;": "Ú",
                "&Ucirc;": "Û",
                "&Uuml;": "Ü",
                "&Yacute;": "Ý",
                "&thorn;": "Þ",
                "&szlig;": "ß",
                "&agrave;": "à",
                "&aacute;": "á",
                "&acirc;": "â",
                "&atilde;": "ã",
                "&auml;": "ä",
                "&aring;": "å",
                "&aelig;": "æ",
                "&ccedil;": "ç",
                "&egrave;": "è",
                "&eacute;": "é",
                "&ecirc;": "ê",
                "&euml;": "ë",
                "&igrave;": "ì",
                "&iacute;": "í",
                "&icirc;": "î",
                "&iuml;": "ï",
                "&eth;": "ð",
                "&ntilde;": "ñ",
                "&ograve;": "ò",
                "&oacute;": "ó",
                "&ocirc;": "ô",
                "&otilde;": "õ",
                "&ouml;": "ö",
                "&divide;": "÷",
                "&oslash;": "ø",
                "&ugrave;": "ù",
                "&uacute;": "ú",
                "&ucirc;": "û",
                "&uuml;": "ü",
                "&yacute;": "ý",
                "&thorn;": "þ",
                "&yuml;": "ÿ",
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
