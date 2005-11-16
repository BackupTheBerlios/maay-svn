import cStringIO

import maay.globalvars

class TemplateFile:

    def __init__(self, filename):
        self.templateVars = None
        self.read(filename)

    def read(self, filename):
        fd = file(filename)
        self.templateVars = {}
        state = 0
        line_num = 1
        varName = None
        varValue = None

        line=' '

        while line:
            line = fd.readline()

            # waiting for <!--< begin var >-->
            if state == 0:
                words = line.split()
                if len(words) != 0:
                    if words[0] != "<!--<" or (words[1] != "begin" and words[1] != "rem") or words[len(words) - 1] != '>-->':
                        raise "Error on line %d: <!--< begin var >--> expected or <!--< rem remarks >--> , find '%s' instead" % (line_num, line)
                    if words[1] == "begin":
                        if len(words) != 4:
                            raise "Error on line %d: <!--< begin var >--> expected, find '%s' instead" % (line_num, line)
                        varName = words[2]
                        varValue = ["", []]
                        varPos = 0
                        state = 1
            elif state == 1:
                words = line.split()

                if len(words) > 2 and words[0] == '<!--<' and words[1] != 'value' and (len(words) != 4 or words[1] != 'end' or words[2] != varName or words[3] != '>-->'):
                    raise "Error on line %d: <!--< end %s >--> expected, find '%s' instead" % (line_num, varName, line)

                if len(words) > 2 and words[0] == '<!--<' and words[1] != 'value' and words[1] == 'end':
                    self.templateVars[varName] = varValue
                    state = 0
                else:
                    # search for <!--< value variable >-->
                    start = 0
                    new_line = ""
                    end = 0
                    old_end = 0
                    while 1:
                        start = line.find("<!--<", start + 1)
                        if start == -1:
                            break
                        end = line.find(">-->", start + 5) + 4
                        if end == 3:
                            raise "Error on line %d: column %d: '>-->' expected" % (line_num, start)
                        tagContent = line[start:end]
                        words = tagContent.split()
                        if len(words) != 4 or words[1] != "value":
                            raise "Error on line %d: column %d: '<!--< value var >-->' expected" % (line_num, start)

                        new_line += line[old_end:start]

                        varPos += start - old_end
                        varValue[1].append((words[2], varPos))

                        old_end = end

                    varPos += len(line) - end
                    new_line += line[end:]
                    varValue[0] += new_line
#                                       offset += len(line) - old_end

            line_num += 1

        if state == 1:
            raise "Error at the end of the file: <!--< end %s >--> expected" % varName

        fd.close()
                        

    def getTemplateValue(self, varName, dict = {}):
        templateVar = self.templateVars[varName]
        
        templateVarStr = cStringIO.StringIO(self.templateVars[varName][0])
        
        result = cStringIO.StringIO()
        i = 0
        for (var, pos) in templateVar[1]:
            value = dict.get(var)
            if value != None:
                v = str(value)
            else:
                value = maay.globalvars.language.getValue(var)
                if value != None:
                    v = str(value)
                else:
                    value = maay.constants.getValue(var)
                    if value != None:
                        v = str(value)
                    else:
                        v = ''
            result.write(templateVarStr.read(pos - i))
#                       result.write(templateVarStr[0][i:pos])
            result.write(v)
            i = pos
        result.write(templateVarStr.read())
        return result.getvalue()


                
