import logging
logging.basicConfig(level=logging.ERROR)

class Scanner():
    lineno = 0

    def __init__(self,f):
        self.file = f
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
            '{': "Brace",
            '}': "Brace",
            ')': "Paren",
            ']': "Bracket",
            ';': "Semicolon",
            ",": "Comma",
            ".": "Period"
        }

        self.nextChar = ''
        self.stop = {'(', ')', '[', ']', ';', ',', ':', '.','-', '{', '}', }
        self.ignore = {'\s', ' ', '\n', '\r', '\t'}

        self.reserved = {'program','is','begin','end', 'global',
                'procedure','variable','type','integer','float',
                'string','bool','enum','if','then','else','for',
                'not','return','true','false'}
                

    def cont(self, string):
        return string.isalpha() or string.isdigit() or string=='_'
    
    def readFile(self):
        with open(self.file, 'r') as r:
            for line in r:
                Scanner.lineno += 1
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
            try:
                if self.nextChar != '':
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
                        logging.debug('returning: ({},{})'.format('String', token))
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
                            yield ('Divide', token)
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
                        logging.debug('returning: ({},{})'.format('Relation', token))
                        yield ('Relation', token)

                    elif self.types[token] == 'AssignmentIndex':
                        tmp = next(c)
                        if tmp == "=":
                            logging.debug('returning: ({},{})'.format('Assignment', token+tmp))
                            yield ('Assignment', token+tmp)
                        elif tmp.isdigit():
                            self.nextChar = tmp
                            logging.debug('returning: ({},{})'.format('Index', token))
                            yield('Index', token)
                        else:
                            # Is part of declaration?
                            self.nextChar = tmp
                            logging.debug('returning: ({},{})'.format('Colon', token))
                            yield ('Colon', ':')
                            
                            # TODO: error

                    else:
                        logging.debug('returning: ({},{})'.format(self.types[token], token))
                        yield (self.types[token], token)

                else:
                    if token.isdigit():
                        # TODO: enforce [0-9][0-9_]*[.[0-9]*]
                        tmp = next(c)
                        
                        while tmp not in self.stop and tmp not in self.ignore and tmp not in self.types or tmp == '.':
                            token += tmp
                            tmp = next(c)

                        self.nextChar = tmp
                        logging.debug('returning: ({},{})'.format('Digit', token))

                        yield ('Digit', token)
                    else:
                        tmp = next(c)
                        if tmp.isalpha():
                            while self.cont(tmp):
                                token += tmp
                                tmp = next(c)
                    
                        else:
                            while tmp not in self.stop and tmp not in self.ignore and token not in self.types and tmp not in self.types:
                                token += tmp
                                tmp = next(c)

                        self.nextChar = tmp

                        if token in self.reserved:
                            
                            logging.debug('returning: ({},{})'.format('Keyword', token))
                            yield ('Keyword', token)
                        else:
                            logging.debug('returning: ({},{})'.format('Identifier', token))
                            yield ('Identifier', token)

            except StopIteration:
                # TODO: maybe need to also yield last token that stop got caught on?
                logging.debug('returning: ({},{})'.format('EOF', 'eof'))
                yield ('EOF', 'eof')
                break

# s = Scanner()
# tmp = s.scan()
# while True:
#     logging.debug(next(tmp))

