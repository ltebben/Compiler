from scanproto2 import Scanner
import json


class Parser():
    def __init__(self):
        self.scanner = Scanner()
        self.token = self.scanner.scan()
        self.curr_token = ''

        self.carry = ''
        self.program()

        # while True:
        #     token = next(self.token)
        #     if token[0] == 'Keyword':
        #         if token[1] == 'end':
        #             token = next(self.token)
        #         elif token[1] == 'if':
        #
        #             self.if_statement()

    def write_error(self, expected_type, expected_token, received_token):
        print(json.dumps({'error': 'missing {}'.format(expected_type), 'details': "expected '{}', got '{}'".format(
            expected_token, received_token), 'lineno': self.scanner.lineno}))

    def program(self):
        print('expanding program')
        self.program_header()
        self.program_body()

        self.curr_token = next(self.token)
        if self.curr_token != '.':
            self.write_error('period', '.', self.curr_token[1])
            return

    def program_header(self):
        print('expanding program header')
        self.curr_token = next(self.token)
        if self.curr_token[1] != 'program':
            self.write_error('program', 'program', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[1] != 'is':
            self.write_error('is', 'is', self.curr_token[1])
            return

    def program_body(self):
        print('expanding program body')
        self.curr_token = next(self.token)

        while self.curr_token[1] != 'begin':
            self.declaration()
            self.curr_token = next(self.token)
            if self.curr_token[1] != ';':
                self.write_error('semicolon', ';', self.curr_token[1])
                return
            self.curr_token = next(self.token)

        # Now it is begin, so skip to the next token
        print("MOVING ON TO PROGRAM CODE FINALLY")
        self.curr_token = next(self.token)

        while self.curr_token[1] != 'end':
            self.statement()

        # Now it is end, so skip to the next token
        self.curr_token = next(self.token)
        if self.curr_token[1] != 'program':
            self.write_error('end program', 'end program', self.curr_token[1])
            return

    def declaration(self):
        print('expanding declaration')
        if self.curr_token[1] == 'global':
            self.curr_token = next(self.token)
            # TODO: add to global symbol table

        if self.curr_token[1] == 'procedure':
            self.procedure_declaration()
        elif self.curr_token[1] == 'variable':
            self.variable_declaration()
        elif self.curr_token[1] == 'type':
            self.type_declaration()
        else:
            self.write_error(
                'declaration', '"procedure","variable", or "type"', self.curr_token[1])
            return

    def procedure_declaration(self):
        print('expanding procedure declaration')
        self.procedure_header()
        self.procedure_body()

    def procedure_header(self):
        print('expanding procedure header')
        self.curr_token = next(self.token)
        if self.curr_token[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[1] != ':':
            self.write_error('colon', ':', self.curr_token[1])
            return

        self.type_mark()

        self.curr_token = next(self.token)
        if self.curr_token[1] != '(':
            self.write_error('parenthesis', '(', self.curr_token[1])
            return

        self.parameter_list()

        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)

        if self.curr_token[1] != ')':
            self.write_error('parenthesis', ')', self.curr_token[1])
            return

    def type_mark(self):
        print('expanding type mark')
        self.curr_token = next(self.token)
        if self.curr_token[1] not in ['integer', 'float', 'string', 'bool']:
            if self.curr_token[1] == 'enum':
                self.enum()
            elif self.curr_token[0] != 'Identifier':
                self.write_error('type', '<type>', self.curr_token[1])
                return

    def parameter_list(self):
        print('expanding parameter list')
        self.parameter()

        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)

        if self.curr_token[1] == ',':
            self.parameter_list()
        else:
            self.carry = self.curr_token

    def parameter(self):
        print('expanding parameter')
        self.curr_token = next(self.token)
        if self.curr_token[1] != 'variable':
            self.write_error('variable', 'variable', self.curr_token[1])
            return
        self.variable_declaration()

    def enum(self):
        print('expanding enum')
        self.curr_token = next(self.token)
        if self.curr_token[1] != '{':
            self.write_error('brace', '{', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        while self.curr_token[1] != '}':
            if self.curr_token[1] != ',':
                self.write_error('comma', ',', self.curr_token[1])
                return
            self.curr_token = next(self.token)
            if self.curr_token[0] != 'Identifier':
                self.write_error('identifier', '<identifier>', self.curr_token[1])
                return
            self.curr_token = next(self.token)

    def procedure_body(self):
        print('expanding procedure body')

        self.curr_token = next(self.token)
        print(self.curr_token)
        while self.curr_token[1] != 'begin':
            self.declaration()
            if self.carry:
                self.curr_token = self.carry
                self.carry = ''
            else:
                self.curr_token = next(self.token)
            print(self.curr_token)
            if self.curr_token[1] != ';':
                self.write_error('semicolon', ';', self.curr_token[1])
                return
            self.curr_token = next(self.token)

        # Now token is begin, so read the next one
        print("FOUND THE PROCEDURE BEGIN")
        self.curr_token = next(self.token)
        while self.curr_token[1] != 'end':
            print("pre " + str(self.curr_token))
            self.statement()
            self.curr_token = next(self.token)
            print("This is where i am " + str(self.curr_token))

        print("FOUND THE PROCEDURE END")
        # Now token is end, so read the next one
        self.curr_token = next(self.token)
        if self.curr_token[1] != 'procedure':
            self.write_error('end procedure', 'end procedure', self.curr_token[1])

            return
        
        print("RETURN CONTROL TO PROGRAM")

    def statement(self):
        print('expanding statement')
        if self.curr_token[1] == 'if':
            self.if_statement()
        elif self.curr_token[1] == 'for':
            self.for_statement()
        elif self.curr_token[1] == 'return':
            self.return_statement()
        else:
            print("Here i am "+str(self.curr_token))
            self.assignment_statement()

    def for_statement(self):
        print('expanding for statement')
        self.curr_token = next(self.token)
        if self.curr_token[1] != '(':
            self.write_error('parenthesis', '(', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        self.assignment_statement()

        self.curr_token = next(self.token)
        if self.curr_token[1] != ';':
            self.write_error('semicolon', ';', self.curr_token[1])
            return

        self.expression()

        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)

        if self.curr_token[1] != ')':
            self.write_error('parenthesis', ')', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        while self.curr_token[1] != 'end':
            self.statement()
            self.curr_token = next(self.token)
            if self.curr_token != ';':
                self.write_error('semicolon', ';', self.curr_token[1])
                return
            self.curr_token = next(self.token)

        # Now it's end, so move on to next token
        self.curr_token = next(self.token)
        if self.curr_token[1] != 'for':
            self.write_error('end for', 'end for', self.curr_token[1])
            return

    def return_statement(self):
        print('expanding return statement')
        self.expression()

    def assignment_statement(self):
        print('expanding assignment statement')
        self.destination()

        # Destination checks for bounds [], so if it didn't find a [, need to check what it did find
        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)

        if self.curr_token[1] != ':=':
            self.write_error('assignment operator', ':=', self.curr_token[1])
            return

        self.expression()

    def destination(self):
        print('expanding destination')
        #self.curr_token = next(self.token)
        if self.curr_token[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[1] == '[':
            self.expression()
            self.curr_token = next(self.token)
            if self.curr_token[1] != ']':
                self.write_error('bracket', ']', self.curr_token[1])
                return
        else:
            self.carry = self.curr_token

    def variable_declaration(self):
        print('expanding variable declaration')
        self.curr_token = next(self.token)
        if self.curr_token[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[1] != ':':
            self.write_error('colon', ':', self.curr_token[1])
            return
        print("here???")
        self.type_mark()

        self.curr_token = next(self.token)
        if self.curr_token[1] == '[':
            self.bound()
            self.curr_token = next(self.token)
            if self.curr_token[1] != ']':
                self.write_error('bracket', ']', self.curr_token[1])
                return
        else:
            self.carry = self.curr_token

    def type_declaration(self):
        print('expanding type declaration')
        self.curr_token = next(self.token)
        if self.curr_token[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[1] != 'is':
            self.write_error('is', 'is', self.curr_token[1])
            return

        self.type_mark()

    def if_statement(self):
        print('expanding if statement')

        self.curr_token = next(self.token)
        print('this 2 '+str(self.curr_token))
        if self.curr_token[1] != '(':
            self.write_error('parenthesis', '(', self.curr_token[1])
            return

        self.expression()
        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)
        print(self.curr_token)
        if self.curr_token[1] != ')':
            self.write_error('parenthesis', ')', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[1] != 'then':
            self.write_error('then', 'then', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        self.statement()

        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)

        if self.curr_token[1] != ';':
            self.write_error('semicolon', ';', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        while not (self.curr_token[1] == 'else' or self.curr_token[1] == 'end'):
            self.statement()
            self.curr_token = next(self.token)

        # Now it is else or end
        if self.curr_token[1] == 'else':
            self.curr_token = next(self.token)
            while not (self.curr_token[1] == 'else' or self.curr_token[1] == 'end'):
                self.statement()
                self.curr_token = next(self.token)

        if self.curr_token[1] != 'end':
            self.write_error('end', 'end', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[1] != 'if':
            self.write_error('end if', 'end if', self.curr_token[1])
            return

        self.curr_token = next(self.token)
        if self.curr_token[1] != ';':
            self.write_error('semicolon', ';', self.curr_token[1])
            return

    def bound(self):
        print('expanding bound')
        self.curr_token = next(self.token)
        if self.curr_token == '-':
            self.curr_token = next(self.token)

        if self.curr_token[0] != 'Digit':
            self.write_error('digit', '<digit>', self.curr_token[1])
            return

    def expression(self):
        print('expanding expression')
        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)
        print("value in expression is " + str(self.curr_token))
        if self.curr_token[1] == 'not':
            self.curr_token = next(self.token)

        self.arithOp()
        print("value in expression after arithOp is " + str(self.curr_token))
        # acceptable
        if self.curr_token[1] == '&':
            self.expression()
        elif self.curr_token[1] == '|':
            self.expression()

        self.carry = self.curr_token

    def arithOp(self):
        print('expanding arithOp')
        self.relation()
        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)
        print("value in arithop after relation is " + str(self.curr_token))
        if self.curr_token[1] == '+':
            self.curr_token = next(self.token)
            self.arithOp()
        elif self.curr_token[1] == '-':
            self.curr_token = next(self.token)
            self.arithOp()
        else:
            self.carry = self.curr_token
        print("The carry is "+str(self.carry))

    def relation(self):
        print('expanding relation')
        self.term()
        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)
        print("value in relation after term is " + str(self.curr_token))
        if self.curr_token[1] in ['<', '<=', '>', '>=', '==', '!=']:
            self.curr_token = next(self.token)
            self.relation()
        else:
            self.carry = self.curr_token
        print("The carry is "+str(self.carry))

    def term(self):
        print('expanding term')
        self.factor()
        if self.carry:
            self.curr_token = self.carry
            self.carry = ''
        else:
            self.curr_token = next(self.token)
            print("value in term after factor is " + str(self.curr_token))
        if self.curr_token[1] == '*' or self.curr_token[1] == '/':
            self.curr_token = next(self.token)
            self.term()
        else:
            self.carry = self.curr_token
        print("The carry is "+str(self.carry))

    def factor(self):
        print('expanding factor')
        if self.curr_token[1] == '(':
            self.expression()
        elif self.curr_token[0] == 'String':
            print('acceptable: string')
        elif self.curr_token[1] == 'true' or self.curr_token[1] == 'false':
            print('acceptable: bool')
        elif self.curr_token[1] == '-':
            self.curr_token = next(self.token)
            if self.curr_token[0] == 'Digit':
                print('acceptable: negative digit')
            elif self.curr_token[0] == 'Identifier':
                self.name()
            else:
                self.write_error('digit or identifier',
                                 '<digit> or <identifier>', self.curr_token[1])
                return
        elif self.curr_token[0] == 'Digit':
            print('acceptable: digit')
        elif self.curr_token[0] == 'Identifier':
            print('name or procedure call?')
            self.name_or_procedure()
        else:
            self.write_error('(, <string>, <bool>, -, <digit>, <identifier>',
                         '(, <string>, <bool>, -, <digit>, <identifier>', self.curr_token[1])

    def name_or_procedure(self):
        print('expanding name or procedure')
        self.curr_token = next(self.token)
        if self.curr_token[1] == '(':
            self.procedure_call()
        else:
            self.name()

    def name(self):
        print('expanding name')
        if self.curr_token[1] == '[':
            self.expression()
            if self.curr_token[1] != ']':
                self.write_error('bracket', ']', self.curr_token[1])
                return
        else:
            self.carry = self.curr_token

    def procedure_call(self):
        print('expanding procedure call')
        self.argument_list()

    def argument_list(self):
        print('expanding argument list')
        self.expression()
        self.curr_token = next(self.token)
        if self.curr_token[1] == ',':
            self.argument_list()
        else:
            self.carry = self.curr_token


p = Parser()
