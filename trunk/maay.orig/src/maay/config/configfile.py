"""
        Analyse configuration file.
        The format of a config file is the following:
                Var     Value
                Var2    Value2
        All caracters after a '#' are ignored (comments).
"""

import os

STRING_TYPE = 0
INT_TYPE = 1
FILENAME_TYPE = 2
DIRNAME_TYPE = 3
CHOICE_TYPE = 4
LIST_TYPE = 5

OPTIONNAL_VARIABLE = 0
MANDATORY_VARIABLE = 1

class ConfigFile:

    # filename: the configuration filename
    # variableTypes: dictionnary of variables that can be used in the configuration file:
    #       variableTypes = {
    #                               'var' : (TYPE, OPTIONNAL_VARIABLE | MANDATORY_VARIABLE)
    #                       }

    def __init__(self, filename, variableTypes):
        self.__variableTypes = variableTypes
        self.__filename = filename
        self.__variables = {}
        fd = file(filename, 'r')
        line_num = 1
        while 1:
            line = fd.readline()
            if line == '':
                break

            pos_sharp = line.find('#')
            if pos_sharp != -1:
                line = line[:pos_sharp]

            line = line.strip()
            if line == '':
                continue
        
            words = line.split(None, 1)
            if len(words) < 2:
                raise "%s: value expected for variable '%s' at line %d" % (filename, words[0], line_num)
            var = words[0].strip()
            value = words[1].strip()
            if variableTypes.has_key(var):
                var_type = variableTypes[var][0]

                if var_type != LIST_TYPE and self.__variables.has_key(var):
                    print "warning: variable '%s' redefined at line  %d" % (var, line_num)

                if var_type == STRING_TYPE:
                    self.__variables[var] = value
                elif var_type == INT_TYPE:
                    self.__variables[var] = int(value)
                elif var_type == DIRNAME_TYPE:
                    self.__variables[var] = os.path.abspath(value)
                elif var_type == FILENAME_TYPE:
                    self.__variables[var] = os.path.abspath(value)
                elif var_type == CHOICE_TYPE:
                    choices = variableTypes[var][2]
                    if not value in choices:
                        raise "Variable '%s' at line %d can only takes the value: %s" % (var, choices)
                    self.__variables[var] = value
                elif var_type == LIST_TYPE:
                    values = self.__variables.get(var)
                    if not values:
                        self.__variables[var] = [ value ]
                    else:
                        values.append(value)                                                                            
            else:
                raise "%s: variable '%s' not expected at line %d" % (filename, var, line_num)

            line_num += 1

        for var in variableTypes.keys():
            if not self.__variables.has_key(var) and variableTypes[var][1] == 1:
                raise "variable '%s' has not been set in config file" % var

    # get variable value
    def getValue(self, var):
        return self.__variables.get(var)


    # set variable value
    def setValue(self, var, value):
        self.__variables[var] = value

    # save configuration file
    def save(self):
        fd = file(self.__filename, "wb")
        for var, value in self.__variables.items():
            if self.__variableTypes[var][0] == LIST_TYPE:
                if value:
                    for v in value:
                        fd.write("%s %s\r\n" % (var, v))                                                
            else:
                fd.write("%s %s\r\n" % (var, value))    
        fd.close()
