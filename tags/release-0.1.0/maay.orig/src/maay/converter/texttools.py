import re

accents = (
                (('é', 'è', 'ë', 'ê'), 'e'),
                (('ï', 'î'), 'i'),
                (('à', 'ä', 'â'), 'a'),
                (('ô'), 'u'),
                (('ù', 'ü', 'û'), 'u'),
                (('ù', 'ÿ', 'y'), 'u'),
                (('ç'), 'c'),
                (('É', 'È', 'Ê', 'Ë'), 'E'),
                (('À', 'Â'), 'A'),
                (('Ù', 'Û', 'Ü'), 'U'),
                (('Ô'), 'O'),
                (('Î'), 'Ï'),
                (('Ç'), 'C')
        )

regex_accents = {
                'e': "é|è|ë|ê",
                'i': "ï|î",
                'a': "à|ä|â",
}

without_accents = {
                'é':'e',
                'è':'e',
                'ë':'e',
                'ê':'e',
                'ï':'i',
                'î':'i',
                'à':'a',
                'ä':'a',
                'â':'a',
                'ô':'o',
                'ù':'u',
                'ü':'u',
                'û':'u',
                'ÿ':'y',
                'ç':'c',
                'É':'E',
                'È':'E',
                'Ê':'E',
                'Ë':'E',
                'À':'A',
                'Â':'A',
                'Ù':'U',
                'Û':'U',
                'Ü':'U',
                'Ô':'O',
                'Î':'I',
                'Ï':'I',
                'Ç':'C'
        }


def __repl(matchobj):
    global without_accents

    l = without_accents.get(matchobj.group(0))
    if l:
        return l
    return matchobj.group(0)

def replaceAccent(data):
    return re.sub(globalvars.accent.getRegularExpression(), __repl, data)

def stripWhiteSpaces(data):
    d = re.sub("\s+", " ", data)
    return d.strip()

def replaceToRegularExpressionWithAccents(regex):
    pass
    
def isAlphaNum(c):
    return (c >= 'a' and c <= 'z') or (c >='A' and c <= 'Z') or (c >='0' and c <= '9')

def isAlpha(c):
    return (c >= 'a' and c <= 'z') or (c >='A' and c <= 'Z')

def isSpace(c):
    return c in (' ', '\t', '\r', '\n')

def isSpace(c):
    return c in (' ', '     ', '\r', '\n')

def levenshtein_distance(a,b):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
    # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*m
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]

def excerpt(s, length, cut_to_word=0):
    if len(s) < length:
        return s
    else:
        if not cut_to_word:
            return "%s..." % s[:length]
#               else:
#                       end = length

                
# TODO: faire une librairie pour traiter le texte et html (operation comme representer la date (format court ou long),
# afficher une taille de fichier, ...
def size2str(s):
    if s < 1024:
        return "%d bytes" % s 
    elif s < 1048576:
        return "%.1f k" % (float(s) / 1024)
    else:
        return "%.1f M" % (float(s) / 1048576)

def date2str(t):
    return time.strftime("%d %b %Y", time.localtime(t))

def __to_url(u):
    return u.replace('\\', '/')

