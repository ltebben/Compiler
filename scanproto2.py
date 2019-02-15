class Scanner():
    def __init__(self):
        self.lineno = 0
        self.types = {
            '\"': "String",
            '/': "CommentDivide",
            '+': "ArithOp",
            '-': "ArithOp",
            '*': "Times",
            ':': "AssignmentIndex",
            '&': "And",
            '|': "Or",
            '<': "Relation",
            '>': "Relation",
            '<=': "Relation",
            '>=': "Relation",
            '==': "Relation",
            '!=': "Relation",
            '(': "Paren",
            '[': "Bracket",
            ')': "Paren",
            ']': "Bracket",
            ';': "Semicolon",
            ",": "Comma",
            ".": "Period"
        }

        self.nextChar = ''
        self.stop = set(['(', ')', '[', ']', ';', ',', ':', '.'])
        self.ignore = set(['\s', ' ', '\n', '\r', '\t'])

        self.reserved = set(['program','is','begin','end', 'global',
                'procedure','variable','type','integer','float',
                'string','bool','enum','if','then','else','for',
                'not','return','true','false'])

    def readFile(self):
        with open('testPgms/correct/test1.src', 'r') as r:
            for line in r:
                self.lineno += 1
                line = line.lower()
                yield line

    def nextword(self):
        line = self.readFile()
        for l in line:
            for char in l:
                yield char

    def nextchar(self):
        char = self.nextword()
        for c in char:
            yield c

    def eraseBlockComment(self, c):
        token = next(c)
        while token[-2::] != '*/':
            token += next(c)
            if token[-2::] == '/*':
                self.eraseBlockComment(c)
        return token

    def scan(self):
        c = self.nextchar()
        while True:
            if self.nextChar:
                token = self.nextChar
                self.nextChar = ''
            else:
                token = next(c)

            while token in self.ignore:
                token = next(c)

            if token in self.types:
                if self.types[token] == 'String':
                    token += next(c)
                    while token[-1] != '"':
                        token += next(c)
                    yield ('String', token)

                elif self.types[token] == 'CommentDivide':
                    tmp = next(c)

                    if tmp == '*':
                        # Found block comment -- erase
                        token = self.eraseBlockComment(c)
                    elif tmp == '/':
                        # Found line comment -- erase
                        while token[-1] != '\n':
                            token += next(c)
                    elif tmp.isdigit():
                        # Found division -- save digit for later
                        self.nextChar = tmp
                    # TODO: Keep processing for next real token
                    continue

                elif self.types[token] == 'Relation':
                    tmp = next(c)
                    if tmp.isdigit():
                        self.nextChar = tmp
                    elif tmp == "=":
                        token += tmp
                    else:
                        pass
                        # TODO: error
                    yield ('Relation', token)

                elif self.types[token] == 'AssignmentIndex':
                    tmp = next(c)

                    if tmp == "=":
                        yield ('Assignment', token+tmp)
                    elif tmp.isdigit():
                        yield('Index', token)
                        self.nextChar = tmp
                    else:
                        pass
                        # TODO: error

                else:
                    yield (self.types[token], token)

            else:
                if token.isdigit():
                    # TODO: enforce [0-9][0-9_]*[.[0-9]*]
                    tmp = next(c)
                    if not tmp.isdigit():
                        while tmp == '_':
                            tmp = next(c)
                        if not tmp.isdigit() or tmp!='_':
                            pass
                            # TODO: error

                    while not (tmp in self.ignore or tmp in self.stop):
                        token += tmp
                        tmp = next(c)
                    self.nextChar = tmp

                    yield ('Digit', token)
                else:
                    tmp = next(c)

                    while not (tmp in self.ignore or tmp in self.stop):
                        token += tmp
                        tmp = next(c)

                    self.nextChar = tmp

                    if token in self.reserved:
                        yield ('Keyword', token)
                    else:
                        yield ('Identifier', token)


s = Scanner()
gen = s.scan()
while True:
    print(next(gen))
