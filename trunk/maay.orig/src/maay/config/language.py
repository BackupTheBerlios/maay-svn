import glob
import os.path

class Language:
    def __init__(self, language_directory, language = 'english'):
        self.__language_directory = language_directory
        language_files = glob.glob1(language_directory, "*.lang")
        self.__languages = []
        self.__language = language
        self.__variables = None

        for f in language_files:
            self.__languages.append(f.rstrip('.lang'))
        self.setLanguage(language)              


    def setLanguage(self, language):
        try:
            fd = file(os.path.join(self.__language_directory, "%s.lang" % language))
        except Exception, e:
            raise "language: %s" % e
        self.__language = language
        self.__variables = {}
        line_num = 0
        while True:
            line_num += 1

            line = fd.readline()
            if not line:
                break

            parts = line.split("=", 1)

            if len(parts) == 0:
                continue
                
            var = parts[0].strip()

            if (len(parts) == 1 and len(var) == 0) or var[0] == '#':
                continue

            if len(parts) != 2:
                raise "%s: Error line %d" % (filename, line_num)
            value = parts[1].strip()
            self.__variables[var] = value
        fd.close()

    def getLanguage(self):
        return self.__language

    def getLanguages(self):
        return self.__languages
                
    def getValue(self, var):
        return self.__variables.get(var)
