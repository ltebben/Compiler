from scanproto2 import Scanner
import json
import inspect 


class Parser():
    def __init__(self):
        self.scanner = Scanner()
        self.token = self.scanner.scan()

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

    def write_error(self, expected_type, expected_token, received_token, function):
        print(json.dumps({'error': 'missing {}'.format(expected_type), 'details': "expected '{}', got '{}'".format(
            expected_token, received_token), 'lineno': self.scanner.lineno, 'traceback':function}))

    def program(self):
        print('expanding program')
        self.program_header()
        self.program_body()

        tmp = next(self.token)
        if tmp != '.':
            self.write_error('period', '.', tmp[1], inspect.stack()[0][3])
            return

    def program_header(self):
        print('expanding program header')
        tmp = next(self.token)
        if tmp[1] != 'program':
            self.write_error('program', 'program', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[1] != 'is':
            self.write_error('is', 'is', tmp[1], inspect.stack()[0][3])
            return

    def program_body(self):
        print('expanding program body')
        tmp = next(self.token)

        while tmp[1] != 'begin':
            self.declaration(tmp)
            tmp = next(self.token)
            if tmp[1] != ';':
                self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
                return
            tmp = next(self.token)

        # Now it is begin, so skip to the next token
        print("MOVING ON TO PROGRAM CODE FINALLY")
        tmp = next(self.token)

        while tmp[1] != 'end':
            self.statement(tmp)

        # Now it is end, so skip to the next token
        tmp = next(self.token)
        if tmp[1] != 'program':
            self.write_error('end program', 'end program', tmp[1], inspect.stack()[0][3])
            return

    def declaration(self, tmp):
        print('expanding declaration')
        if tmp[1] == 'global':
            tmp = next(self.token)
            # TODO: add to global symbol table

        if tmp[1] == 'procedure':
            self.procedure_declaration()
        elif tmp[1] == 'variable':
            self.variable_declaration()
        elif tmp[1] == 'type':
            self.type_declaration()
        else:
            self.write_error(
                'declaration', '"procedure","variable", or "type"', tmp[1], inspect.stack()[0][3])
            return

    def procedure_declaration(self):
        print('expanding procedure declaration')
        self.procedure_header()
        self.procedure_body()

    def procedure_header(self):
        print('expanding procedure header')
        tmp = next(self.token)
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[1] != ':':
            self.write_error('colon', ':', tmp[1], inspect.stack()[0][3])
            return

        self.type_mark()

        tmp = next(self.token)
        if tmp[1] != '(':
            self.write_error('parenthesis', '(', tmp[1], inspect.stack()[0][3])
            return

        self.parameter_list()

        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)

        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return

    def type_mark(self):
        print('expanding type mark')
        tmp = next(self.token)
        if tmp[1] not in ['integer', 'float', 'string', 'bool']:
            if tmp[1] == 'enum':
                self.enum()
            elif tmp[0] != 'Identifier':
                self.write_error('type', '<type>', tmp[1], inspect.stack()[0][3])
                return

    def parameter_list(self):
        print('expanding parameter list')
        self.parameter()

        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)

        if tmp[1] == ',':
            self.parameter_list()
        else:
            self.carry = tmp

    def parameter(self):
        print('expanding parameter')
        tmp = next(self.token)
        if tmp[1] != 'variable':
            self.write_error('variable', 'variable', tmp[1], inspect.stack()[0][3])
            return
        self.variable_declaration()

    def enum(self):
        print('expanding enum')
        tmp = next(self.token)
        if tmp[1] != '{':
            self.write_error('brace', '{', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        while tmp[1] != '}':
            if tmp[1] != ',':
                self.write_error('comma', ',', tmp[1], inspect.stack()[0][3])
                return
            tmp = next(self.token)
            if tmp[0] != 'Identifier':
                self.write_error('identifier', '<identifier>', tmp[1], inspect.stack()[0][3])
                return
            tmp = next(self.token)

    def procedure_body(self):
        print('expanding procedure body')

        tmp = next(self.token)
        print(tmp)
        while tmp[1] != 'begin':
            self.declaration(tmp)
            if self.carry:
                tmp = self.carry
                self.carry = ''
            else:
                tmp = next(self.token)
            print(tmp)
            if tmp[1] != ';':
                self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
                return
            tmp = next(self.token)

        # Now token is begin, so read the next one
        print("FOUND THE PROCEDURE BEGIN")
        tmp = next(self.token)
        while tmp[1] != 'end':
            print("pre " + str(tmp))
            self.statement(tmp)
            tmp = next(self.token)
            print("This is where i am " + str(tmp))

        print("FOUND THE PROCEDURE END")
        # Now token is end, so read the next one
        tmp = next(self.token)
        if tmp[1] != 'procedure':
            self.write_error('end procedure', 'end procedure', tmp[1], inspect.stack()[0][3])

            return
        
        print("RETURN CONTROL TO PROGRAM")

    def statement(self, tmp):
        print('expanding statement')
        if tmp[1] == 'if':
            self.if_statement()
        elif tmp[1] == 'for':
            self.for_statement()
        elif tmp[1] == 'return':
            self.return_statement()
        else:
            print("Here i am "+str(tmp))
            self.assignment_statement(tmp)

    def for_statement(self):
        print('expanding for statement')
        tmp = next(self.token)
        if tmp[1] != '(':
            self.write_error('parenthesis', '(', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        self.assignment_statement(tmp)

        tmp = next(self.token)
        if tmp[1] != ';':
            self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
            return

        self.expression()

        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)

        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        while tmp[1] != 'end':
            self.statement(tmp)
            tmp = next(self.token)
            if tmp != ';':
                self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
                return
            tmp = next(self.token)

        # Now it's end, so move on to next token
        tmp = next(self.token)
        if tmp[1] != 'for':
            self.write_error('end for', 'end for', tmp[1], inspect.stack()[0][3])
            return

    def return_statement(self):
        print('expanding return statement')
        self.expression()
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
        if tmp[1] != ';':
            self.write_error('semicolon', ';',tmp[1], inspect.stack()[0][3])

    def assignment_statement(self, tmp):
        print('expanding assignment statement')
        self.destination(tmp)

        # Destination checks for bounds [], so if it didn't find a [, need to check what it did find
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)

        if tmp[1] != ':=':
            self.write_error('assignment operator', ':=', tmp[1], inspect.stack()[0][3])
            return

        self.expression()
        print("IN ASSIGNMETN STATAMETN")

    def destination(self, tmp):
        print('expanding destination')
        #tmp = next(self.token)
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[1] == '[':
            self.expression()
            if self.carry:
                tmp = self.carry
                self.carry = ''
            else:
                tmp = next(self.token)
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return
        else:
            self.carry = tmp

    def variable_declaration(self):
        print('expanding variable declaration')
        tmp = next(self.token)
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[1] != ':':
            self.write_error('colon', ':', tmp[1], inspect.stack()[0][3])
            return
        print("here???")
        self.type_mark()

        tmp = next(self.token)
        if tmp[1] == '[':
            self.bound()
            tmp = next(self.token)
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return
        else:
            self.carry = tmp

    def type_declaration(self):
        print('expanding type declaration')
        tmp = next(self.token)
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[1] != 'is':
            self.write_error('is', 'is', tmp[1], inspect.stack()[0][3])
            return

        self.type_mark()

    def if_statement(self):
        print('expanding if statement')

        tmp = next(self.token)
        print('this 2 '+str(tmp))
        if tmp[1] != '(':
            self.write_error('parenthesis', '(', tmp[1], inspect.stack()[0][3])
            return

        self.expression()
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
        print("back in if " +str(tmp))
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[1] != 'then':
            self.write_error('then', 'then', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        self.statement(tmp)

        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)

        if tmp[1] != ';':
            self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        while not (tmp[1] == 'else' or tmp[1] == 'end'):
            self.statement(tmp)
            tmp = next(self.token)

        # Now it is else or end
        if tmp[1] == 'else':
            tmp = next(self.token)
            while not (tmp[1] == 'else' or tmp[1] == 'end'):
                self.statement(tmp)
                tmp = next(self.token)

        if tmp[1] != 'end':
            self.write_error('end', 'end', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[1] != 'if':
            self.write_error('end if', 'end if', tmp[1], inspect.stack()[0][3])
            return

        tmp = next(self.token)
        if tmp[1] != ';':
            self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
            return

    def bound(self):
        print('expanding bound')
        tmp = next(self.token)
        if tmp == '-':
            tmp = next(self.token)

        if tmp[0] != 'Digit':
            self.write_error('digit', '<digit>', tmp[1], inspect.stack()[0][3])
            return

    def expression(self):
        print('expanding expression')
        if self.carry:
            print("There is a carry here that shouldnt' be")
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
        print("value in expression is " + str(tmp))
        if tmp[1] == 'not':
            tmp = next(self.token)

        self.arithOp(tmp)
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
        print("value in expression after arithOp is " + str(tmp))
        # acceptable
        if tmp[1] == '&':
            self.expression()
        elif tmp[1] == '|':
            self.expression()
        else:
            self.carry = tmp

    def arithOp(self,tmp):
        print('expanding arithOp')
        self.relation(tmp)
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
        print("value in arithop after relation is " + str(tmp))
        if tmp[1] == '+':
            tmp = next(self.token)
            self.arithOp(tmp)
        elif tmp[1] == '-':
            tmp = next(self.token)
            self.arithOp(tmp)
        else:
            self.carry = tmp
        print("The carry is "+str(self.carry))

    def relation(self, tmp):
        print('expanding relation')
        self.term(tmp)
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
        print("value in relation after term is " + str(tmp))
        if tmp[1] in ['<', '<=', '>', '>=', '==', '!=']:
            tmp = next(self.token)
            self.relation(tmp)
        else:
            self.carry = tmp
        print("The carry is "+str(self.carry))

    def term(self, tmp):
        print('expanding term')
        self.factor(tmp)
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
            print("value in term after factor is " + str(tmp))
        if tmp[1] == '*' or tmp[1] == '/':
            tmp = next(self.token)
            self.term(tmp)
        else:
            self.carry = tmp
        print("The carry is "+str(self.carry))

    def factor(self, tmp):
        print('expanding factor')
        if tmp[1] == '(':
            self.expression()
        elif tmp[0] == 'String':
            print('acceptable: string')
        elif tmp[1] == 'true' or tmp[1] == 'false':
            print('acceptable: bool')
        elif tmp[1] == '-':
            tmp = next(self.token)
            if tmp[0] == 'Digit':
                print('acceptable: negative digit')
            elif tmp[0] == 'Identifier':
                self.name(tmp)
            else:
                self.write_error('digit or identifier',
                                 '<digit> or <identifier>', tmp[1], inspect.stack()[0][3])
                return
        elif tmp[0] == 'Digit':
            print('acceptable: digit')
        elif tmp[0] == 'Identifier':
            print('name or procedure call?')
            self.name_or_procedure()
        else:
            self.write_error('(, <string>, <bool>, -, <digit>, <identifier>',
                         '(, <string>, <bool>, -, <digit>, <identifier>', tmp[1], inspect.stack()[0][3])

    def name_or_procedure(self):
        print('expanding name or procedure')
        tmp = next(self.token)
        if tmp[1] == '(':
            self.procedure_call()
        else:
            self.name(tmp)

    def name(self, tmp):
        print('expanding name')
        if tmp[1] == '[':
            self.expression()
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return
        else:
            self.carry = tmp

    def procedure_call(self):
        print('expanding procedure call')
        self.argument_list()
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
        if tmp[1] != ')':
            self.write_error('parenthesis',')',tmp[1], inspect.stack()[0][3])


    def argument_list(self):
        print('expanding argument list')
        self.expression()
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
        print("val in argument list after expression "+str(tmp))
        if tmp[1] == ',':
            print("FOUND THE COMMA I WAS LOOKING FOR")
            self.argument_list()
        else:
            self.carry = tmp


p = Parser()
