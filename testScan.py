from scanproto2 import Scanner
import json
import inspect 

class Parser():
    def __init__(self):
        self.scanner = Scanner()
        self.token = self.scanner.scan()

        self.carry = ''
        self.statement(next(self.token))
    
    def write_error(self, expected_type, expected_token, received_token, function):
        print(json.dumps({'error': 'missing {}'.format(expected_type), 'details': "expected '{}', got '{}'".format(
            expected_token, received_token), 'lineno': self.scanner.lineno, 'traceback':function}))

    def statement(self, tmp):
        print('expanding statement')
        # if tmp[1] == 'if':
        #     self.if_statement()
        # elif tmp[1] == 'for':
        #     self.for_statement()
        # elif tmp[1] == 'return':
        #     self.return_statement()
        # else:
        #     print("Here i am "+str(tmp))
        self.assignment_statement(tmp)

    def assignment_statement(self, tmp):
        print('expanding assignment statement')
        self.destination(tmp)

        # Destination checks for bounds [], so if it didn't find a [, need to check what it did find
        if self.carry:
            tmp = self.carry
            self.carry = ''
            print("carry that shouldn't be")
        else:
            tmp = next(self.token)

        if tmp[1] != ':=':
            self.write_error('assignment operator', ':=', tmp[1], inspect.stack()[0][3])
            return

        self.expression()
        if self.carry:
            tmp = self.carry
            self.carry = ''
        else:
            tmp = next(self.token)
        print("Back in assignment, tmp is "+str(tmp))
        if tmp[1] != ';':
            self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
            return
        print("IN ASSIGNMENT STATEMENT")

    def destination(self, tmp):
        print('expanding destination')
        #tmp = next(self.token)
        print("in destination " + str(tmp))
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
            print("assigning {} to carry".format(str(tmp)))

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