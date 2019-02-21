from scanproto2 import Scanner
import json
import inspect 

class Iter():
    def __init__(self):
        self.scanner = Scanner()
        self.token = self.scanner.scan()
        self.curr_token = ''

    def next(self):
        if self.curr_token:
            tmp = self.curr_token
            self.curr_token = ''
            return tmp
        else:
            return next(self.token)
    
    def peek(self):
        if self.curr_token:
            return self.curr_token
        else:
            self.curr_token = next(self.token)
            return self.curr_token 

class Parser():
    def __init__(self):
        tmp = Iter()
        self.token = tmp

        self.statement()

    def write_error(self, expected_type, expected_token, received_token, function):
        print(json.dumps({'error': 'missing {}'.format(expected_type), 'details': "expected '{}', got '{}'".format(
            expected_token, received_token), 'lineno': Scanner.lineno, 'traceback':function}))

    def statement(self):
        print('expanding statement')
        tmp = self.token.peek()
        if tmp[1] == 'if':
            self.if_statement()
        elif tmp[1] == 'for':
            self.for_statement()
        elif tmp[1] == 'return':
            self.return_statement()
        else:
            print("Here i am "+str(tmp))
            self.assignment_statement()

    def return_statement(self):
        print('expanding return statement')
        tmp = self.token.next()
        if tmp[1] != 'return':
            self.write_error('return', 'return',tmp[1], inspect.stack()[0][3])

        self.expression()
        
    def if_statement(self):
        print('expanding if statement')
        tmp = self.token.next()
        if tmp[1] != 'if':
            self.write_error('if', 'if', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[1] != '(':
            self.write_error('parenthesis', '(', tmp[1], inspect.stack()[0][3])
            return

        self.expression()
        
        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[1] != 'then':
            self.write_error('then', 'then', tmp[1], inspect.stack()[0][3])
            return

        self.statement()

        tmp = self.token.next()
        if tmp[1] != ';':
            self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.peek()
        while not (tmp[1] == 'else' or tmp[1] == 'end'):
            self.statement()
            tmp = self.token.next()
            if tmp[1] != ';':
                self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.peek()

        # Now it is else or end
        if tmp[1] == 'else':
            # consume the else
            self.token.next()

            tmp = self.token.peek()
            while tmp[1] != 'end':
                self.statement()
                tmp = self.token.next()
                if tmp[1] != ';':
                    self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
                    return
                print("matching semicolon in if_statement")
                tmp = self.token.peek()

        # should be end now -- consume it
        tmp = self.token.next()
        print(tmp)
        if tmp[1] != 'end':
            self.write_error('end', 'end', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[1] != 'if':
            self.write_error('end if', 'end if', tmp[1], inspect.stack()[0][3])
            return

    def for_statement(self):
        print('expanding for statement')
        tmp = self.token.next()
        if tmp[1] != 'for':
            self.write_error('for', 'for', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[1] != '(':
            self.write_error('parenthesis', '(', tmp[1], inspect.stack()[0][3])
            return

        self.assignment_statement()

        tmp = self.token.next()
        if tmp[1] != ';':
            self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
            return

        self.expression()

        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return
        print("here i am discarding the ) in for_statement")

        tmp = self.token.peek()
        while tmp[1] != 'end':
            print("In the while in for statement " + str(tmp))
            self.statement()
            tmp = self.token.next()
            if tmp[1] != ';':
                self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.peek()

        # Now it's end, so consume the end
        tmp = self.token.next()

        # for needs to follow end
        tmp = self.token.next()
        if tmp[1] != 'for':
            self.write_error('end for', 'end for', tmp[1], inspect.stack()[0][3])
            return

    def assignment_statement(self):
        print('expanding assignment statement')
        self.destination()

        tmp = self.token.next()

        if tmp[1] != ':=':
            self.write_error('assignment operator', ':=', tmp[1], inspect.stack()[0][3])
            return

        self.expression()
        
        print("IN ASSIGNMENT STATEMENT")

    def destination(self):
        print('expanding destination')
        tmp = self.token.next()
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.peek()
        if tmp[1] == '[':
            # Consume it
            self.token.next()

            self.expression()
            
            tmp = self.token.next()
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return

    def expression(self):
        print('expanding expression')
        tmp = self.token.peek()

        if tmp[1] == 'not':
            # Consume it
            tmp = self.token.next()

        self.arithOp()
        
        tmp = self.token.peek()

        # acceptable
        if tmp[1] == '&':
            # Consume &
            self.token.next()
            self.expression()
        elif tmp[1] == '|':
            # Consume |
            self.token.next()
            self.expression()

    def arithOp(self):
        print('expanding arithOp')
        self.relation()
        
        tmp = self.token.peek()
        print("value in arithop after relation is " + str(tmp))
        if tmp[1] == '+':
            tmp = self.token.next()
            self.arithOp()
        elif tmp[1] == '-':
            tmp = self.token.next()
            self.arithOp()

    def relation(self):
        print('expanding relation')
        self.term()
        
        tmp = self.token.peek()
        print("value in relation after term is " + str(tmp))
        if tmp[1] in ['<', '<=', '>', '>=', '==', '!=']:
            tmp = self.token.next()
            self.relation()

    def term(self):
        print('expanding term')
        self.factor()
        
        tmp = self.token.peek()
        print("value in term after factor is " + str(tmp))
        if tmp[1] == '*' or tmp[1] == '/':
            tmp = self.token.next()
            self.term()

    def factor(self):
        print('expanding factor')
        tmp = self.token.peek()
        print("in factor " + str(tmp))
        if tmp[1] == '(':
            self.token.next()
            self.expression()
            tmp = self.token.next()
            if tmp[1] != ')':
                self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            print("here i am discarding the ) in term")
        elif tmp[0] == 'String':
            self.token.next()
            print('acceptable: string')
        elif tmp[1] == 'true' or tmp[1] == 'false':
            self.token.next()
            print('acceptable: bool')
        elif tmp[1] == '-':
            tmp = self.token.next()

            tmp = self.token.peek()
            if tmp[0] == 'Digit':
                self.token.next()
                print('acceptable: negative digit')
            elif tmp[0] == 'Identifier':
                self.name()
            else:
                self.write_error('digit or identifier',
                                 '<digit> or <identifier>', tmp[1], inspect.stack()[0][3])
                return
        elif tmp[0] == 'Digit':
            self.token.next()
            print('acceptable: digit')
        elif tmp[0] == 'Identifier':
            print('name or procedure call?')
            self.name_or_procedure()
        else:
            self.write_error('(, <string>, <bool>, -, <digit>, <identifier>',
                         '(, <string>, <bool>, -, <digit>, <identifier>', tmp[1], inspect.stack()[0][3])

    def name_or_procedure(self):
        print('expanding name or procedure')
        # consume the identifier
        tmp = self.token.next()
        
        tmp = self.token.peek()
        if tmp[1] == '(':
            self.procedure_call()
        else:
            self.name()

    def name(self):
        print('expanding name')
        tmp = self.token.peek()
        if tmp[1] == '[':
            self.expression()
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return

    def procedure_call(self):
        print('expanding procedure call')
        # consume the (
        tmp = self.token.next()
        if tmp[1] != '(':
                self.write_error('parenthesis', '(', tmp[1], inspect.stack()[0][3])
                return

        self.argument_list()
        
        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis',')',tmp[1], inspect.stack()[0][3])

    def argument_list(self):
        print('expanding argument list')
        self.expression()
        
        tmp = self.token.peek()
        print("val in argument list after expression "+str(tmp))
        if tmp[1] == ',':
            print("FOUND THE COMMA I WAS LOOKING FOR")
            # consume the comma
            self.token.next()
            self.argument_list()

p = Parser()