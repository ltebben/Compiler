from scanproto2 import Scanner
import json
import inspect

from llvmlite import ir
import llvmlite.binding as llvm
from ctypes import CFUNCTYPE, c_int64, c_int


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

        self.token = Iter()

        self.symbol_table = [{}, {}]
        self.init_symbol_table()

        self.scope = 1

        self.program()

    def init_symbol_table(self):
        builtins = {
            'getbool': 'bool',
            'getinteger': 'integer',
            'getfloat': 'float',
            'getstring': 'string',
            'putbool': 'bool',
            'putinteger': 'bool',
            'putfloat': 'bool',
            'putstring': 'bool',
            'sqrt': 'float'
        }
        for key, val in builtins.items():
            self.add_entry(key, val, procedure=True, symbol_global=True)

    def check_types(self, type1, type2):
        if type1 == type2:
            return type1
        elif type1 == 'bool' or type2 == 'bool':
            if type1 == 'integer' or type2 == 'integer':
                return 'integer'
        elif type1 == 'integer' or type2 == 'integer':
            if type1 == 'float' or type2 == 'float':
                return 'float'
        
        self.type_error(type1, type2, inspect.stack()[0][3])
        return 'error'

    def add_entry(self, symbol_name, symbol_type, symbol_bound=None, symbol_global=False, procedure=False):
        data = {'type': symbol_type,
                'bound': symbol_bound, 'procedure': procedure}
        if symbol_global:
            self.symbol_table[0][symbol_name] = data
        else:
            self.symbol_table[self.scope][symbol_name] = data
            if procedure:
                self.symbol_table[self.scope-1][symbol_name] = data

    def write_error(self, expected_type, expected_token, received_token, function):
        print(json.dumps({'error': 'missing {}'.format(expected_type), 'details': "expected '{}', got '{}'".format(
            expected_token, received_token), 'lineno': Scanner.lineno, 'traceback': function}))

    def type_error(self, expected_type, received_type, function):
        print(json.dumps({'error': 'type mismatch', 'details': "cannot resolve '{}' and '{}'".format(
            expected_type, received_type), 'lineno': Scanner.lineno, 'traceback': function}))

    def symbol_error(self, var_name, function):
        print(json.dumps({'error': 'variable {} not defined'.format(
            var_name), 'lineno': Scanner.lineno, 'traceback': function}))

    def program(self):
        print('expanding program')
        self.program_header()
        self.program_body()

        tmp = self.token.next()
        if tmp[1] != '.':
            self.write_error('period', '.', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[0] != 'EOF':
            self.write_error('end of file', 'EOF',
                             tmp[1], inspect.stack()[0][3])
            return

        print(self.symbol_table)

    def program_header(self):
        print('expanding program header')
        tmp = self.token.next()
        if tmp[1] != 'program':
            self.write_error('program', 'program',
                             tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>',
                             tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[1] != 'is':
            self.write_error('is', 'is', tmp[1], inspect.stack()[0][3])
            return

    def program_body(self):
        print('expanding program body')

        tmp = self.token.peek()

        while tmp[1] != 'begin':
            self.declaration()
            tmp = self.token.next()
            if tmp[1] != ';':
                self.write_error('semicolon', ';',
                                 tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.peek()

        # Now it is begin, so skip to the next token
        print("MOVING ON TO PROGRAM CODE FINALLY")
        # Consume the begin
        tmp = self.token.next()

        # Move to next token
        tmp = self.token.peek()

        while tmp[1] != 'end':
            self.statement()
            tmp = self.token.next()
            print("Back in program body, tmp is "+str(tmp))
            if tmp[1] != ';':
                self.write_error('semicolon', ';',
                                 tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.peek()

        # Now it is end, so skip to the next token
        # Consume the end
        tmp = self.token.next()
        if tmp[1] != 'end':
            self.write_error('end', 'end', tmp[1], inspect.stack()[0][3])
            return

        # Move on
        tmp = self.token.next()

        if tmp[1] != 'program':
            self.write_error('end program', 'end program',
                             tmp[1], inspect.stack()[0][3])
            return

    def declaration(self):
        print('expanding declaration')
        global_symbol = False
        tmp = self.token.peek()
        if tmp[1] == 'global':
            global_symbol = True
            # Consume the global
            self.token.next()
            # peek at the next value
            tmp = self.token.peek()

        if tmp[1] == 'procedure':
            self.procedure_declaration()
        elif tmp[1] == 'variable':
            symbol_name, symbol_type, symbol_bound = self.variable_declaration()
            self.add_entry(symbol_name, symbol_type,
                           symbol_bound=symbol_bound, symbol_global=global_symbol)
        elif tmp[1] == 'type':
            symbol_name, symbol_type = self.type_declaration()
            self.add_entry(symbol_name, symbol_type,
                           symbol_global=global_symbol)
        else:
            self.write_error(
                'declaration', '"procedure","variable", or "type"', tmp[1], inspect.stack()[0][3])
            return

    def procedure_declaration(self):
        print('expanding procedure declaration')
        self.symbol_table.append({})
        self.scope += 1

        self.procedure_header()
        self.procedure_body()

        self.symbol_table.pop()
        self.scope -= 1

    def procedure_header(self):
        print('expanding procedure header')
        tmp = self.token.next()
        if tmp[1] != 'procedure':
            self.write_error('procedure', 'procedure',
                             tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>',
                             tmp[1], inspect.stack()[0][3])
            return
        symbol_name = tmp[1]

        tmp = self.token.next()
        if tmp[1] != ':':
            self.write_error('colon', ':', tmp[1], inspect.stack()[0][3])
            return

        symbol_type = self.type_mark()

        tmp = self.token.next()
        if tmp[1] != '(':
            self.write_error('parenthesis', '(', tmp[1], inspect.stack()[0][3])
            return

        self.parameter_list()

        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return

        self.add_entry(symbol_name, symbol_type, procedure=True)

    def parameter_list(self):
        print('expanding parameter list')
        self.parameter()

        tmp = self.token.peek()

        if tmp[1] == ',':
            # consume it
            self.token.next()
            self.parameter_list()

    def parameter(self):
        print('expanding parameter')
        symbol_name, symbol_type, symbol_bound = self.variable_declaration()
        self.add_entry(symbol_name, symbol_type, symbol_bound=symbol_bound)

    def procedure_body(self):
        print('expanding procedure body')

        tmp = self.token.peek()
        print(tmp)
        while tmp[1] != 'begin':
            self.declaration()
            tmp = self.token.next()
            print(tmp)
            if tmp[1] != ';':
                self.write_error('semicolon', ';',
                                 tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.peek()

        # Now token is begin, so consume it and read the next one
        tmp = self.token.next()
        if tmp[1] != 'begin':
            self.write_error('begin', 'begin', tmp[1], inspect.stack()[0][3])
            return
        print("FOUND THE PROCEDURE BEGIN")

        tmp = self.token.peek()
        while tmp[1] != 'end':
            self.statement()
            tmp = self.token.next()
            if tmp[1] != ';':
                self.write_error('semicolon', ';',
                                 tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.peek()

        print("FOUND THE PROCEDURE END")
        # Now token is end, so consume it and read the next one
        self.token.next()
        tmp = self.token.next()
        if tmp[1] != 'procedure':
            self.write_error('end procedure', 'end procedure',
                             tmp[1], inspect.stack()[0][3])
            return

        print("RETURN CONTROL TO PROGRAM")

    def variable_declaration(self):
        print('expanding variable declaration')
        tmp = self.token.next()
        if tmp[1] != 'variable':
            self.write_error('variable', 'variable',
                             tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>',
                             tmp[1], inspect.stack()[0][3])
            return

        var_name = tmp[1]

        tmp = self.token.next()
        if tmp[1] != ':':
            self.write_error('colon', ':', tmp[1], inspect.stack()[0][3])
            return

        var_type = self.type_mark()

        var_bound = None
        tmp = self.token.peek()
        if tmp[1] == '[':
            # consume it
            self.token.next()

            var_bound = self.bound()

            tmp = self.token.next()
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return

        return var_name, var_type, var_bound

    def type_declaration(self):
        print('expanding type declaration')
        tmp = self.token.next()
        if tmp[1] != 'type':
            self.write_error('type', 'type', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>',
                             tmp[1], inspect.stack()[0][3])
            return
        var_name = tmp[1]

        tmp = self.token.next()
        if tmp[1] != 'is':
            self.write_error('is', 'is', tmp[1], inspect.stack()[0][3])
            return

        var_type = self.type_mark()

        return var_name, var_type

    def type_mark(self):
        print('expanding type mark')
        tmp = self.token.next()
        if tmp[1] == 'integer':
            pass
        elif tmp[1] == 'float':
            pass
        elif tmp[1] == 'string':
            pass
        elif tmp[1] == 'bool':
            pass
        elif tmp[1] == 'enum':
            self.enum()
        elif tmp[0] == 'Identifier':
            pass
        else:
            self.write_error('type', '<type>', tmp[1], inspect.stack()[0][3])
            return
        return tmp[1]

    def enum(self):
        print('expanding enum')
        tmp = self.token.next()
        if tmp[1] != '{':
            self.write_error('brace', '{', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>',
                             tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        while tmp[1] != '}':
            if tmp[1] != ',':
                self.write_error('comma', ',', tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.next()
            if tmp[0] != 'Identifier':
                self.write_error('identifier', '<identifier>',
                                 tmp[1], inspect.stack()[0][3])
                return

            tmp = self.token.next()

    def bound(self):
        tmp = self.token.next()
        if tmp[0] != 'Digit':
            self.write_error('digit', '<digit>', tmp[1], inspect.stack()[0][3])
            return
        return tmp[1]

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
            self.assignment_statement()

    def return_statement(self):
        print('expanding return statement')
        tmp = self.token.next()
        if tmp[1] != 'return':
            self.write_error('return', 'return', tmp[1], inspect.stack()[0][3])

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
                self.write_error('semicolon', ';',
                                 tmp[1], inspect.stack()[0][3])
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
                    self.write_error('semicolon', ';',
                                     tmp[1], inspect.stack()[0][3])
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
                self.write_error('semicolon', ';',
                                 tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.peek()

        # Now it's end, so consume the end
        tmp = self.token.next()

        # for needs to follow end
        tmp = self.token.next()
        if tmp[1] != 'for':
            self.write_error('end for', 'end for',
                             tmp[1], inspect.stack()[0][3])
            return

    def assignment_statement(self):
        print('expanding assignment statement')
        type1 = self.destination()

        tmp = self.token.next()

        if tmp[1] != ':=':
            self.write_error('assignment operator', ':=',
                             tmp[1], inspect.stack()[0][3])
            return

        type2 = self.expression()
        res = self.check_types(type1, type2)
        print('type in assignment_statement: '+res)

        print("IN ASSIGNMENT STATEMENT")

    def destination(self):
        print('expanding destination')
        tmp = self.token.next()
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>',
                             tmp[1], inspect.stack()[0][3])
            return

        var_name = tmp[1]
        if var_name not in self.symbol_table[self.scope] and var_name not in self.symbol_table[0]:
            self.symbol_error(var_name, inspect.stack()[0][3])

        tmp = self.token.peek()
        if tmp[1] == '[':
            # Consume it
            self.token.next()

            self.expression()

            tmp = self.token.next()
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return

        type1 = self.symbol_table[self.scope][var_name]['type'] if var_name in self.symbol_table[self.scope] else self.symbol_table[0][var_name]['type']
        return type1

    def expression(self):
        print('expanding expression')
        tmp = self.token.peek()

        if tmp[1] == 'not':
            # Consume it
            tmp = self.token.next()

        type1 = self.arithOp()

        tmp = self.token.peek()

        # acceptable
        if tmp[1] == '&' or tmp[1] == '|':
            # Consume &
            self.token.next()
            type2 = self.expression()
            res = self.check_types(type1, type2)
            return res
        else:
            return type1    


    def arithOp(self):
        print('expanding arithOp')
        type1 = self.relation()

        tmp = self.token.peek()
        print("value in arithop after relation is " + str(tmp))
        if tmp[1] == '+' or tmp[1] == '-':
            tmp = self.token.next()
            type2 = self.arithOp()
            res = self.check_types(type1, type2)
            return res
        return type1


    def relation(self):
        print('expanding relation')
        type1 = self.term()

        tmp = self.token.peek()
        print("value in relation after term is " + str(tmp))
        if tmp[1] in ['<', '<=', '>', '>=', '==', '!=']:
            tmp = self.token.next()
            type2 = self.relation()
            res = self.check_types(type1, type2)
            return res
        return type1

    def term(self):
        print('expanding term')
        type1 = self.factor()

        tmp = self.token.peek()
        print("value in term after factor is " + str(tmp))
        if tmp[1] == '*' or tmp[1] == '/':
            tmp = self.token.next()
            type2 = self.term()
            res = self.check_types(type1, type2)
            return res
        return type1

    def factor(self):
        print('expanding factor')
        tmp = self.token.peek()
        print("in factor " + str(tmp))
        if tmp[1] == '(':
            self.token.next()
            type1 = self.expression()
            tmp = self.token.next()
            if tmp[1] != ')':
                self.write_error('parenthesis', ')',
                                 tmp[1], inspect.stack()[0][3])
        elif tmp[0] == 'String':
            self.token.next()
            type1 = 'string'
            print('acceptable: string')
        elif tmp[1] == 'true' or tmp[1] == 'false':
            symbol = self.token.next()
            type1 = 'bool'
            print('acceptable: bool')
        elif tmp[1] == '-':
            tmp = self.token.next()

            tmp = self.token.peek()
            if tmp[0] == 'Digit':
                symbol = self.token.next()
                if '.' in tmp[1]:
                    type1 = 'float'
                else:
                    type1 = 'integer'
                print('acceptable: negative digit')
            elif tmp[0] == 'Identifier':
                type1 = self.name_or_procedure()
            else:
                self.write_error('digit or identifier',
                                 '<digit> or <identifier>', tmp[1], inspect.stack()[0][3])
                return
        elif tmp[0] == 'Digit':
            symbol = self.token.next()
            if '.' in tmp[1]:
                    type1 = 'float'
            else:
                type1 = 'integer'
            print('acceptable: digit')
        elif tmp[0] == 'Identifier':
            print('name or procedure call?')
            type1 = self.name_or_procedure()
        else:
            self.write_error('(, <string>, <bool>, -, <digit>, <identifier>',
                             '(, <string>, <bool>, -, <digit>, <identifier>', tmp[1], inspect.stack()[0][3])
        
        print("type in factor: "+type1)
        return type1

    def name_or_procedure(self):
        print('expanding name or procedure')
        # consume the identifier
        tmp = self.token.next()
        if tmp[1] not in self.symbol_table[self.scope] and tmp[1] not in self.symbol_table[0]:
            self.symbol_error(tmp[1], inspect.stack()[0][3])

        tmp2 = self.token.peek()
        if tmp2[1] == '(':
            self.procedure_call()
        else:
            self.name()
        
        if tmp[1] in self.symbol_table[self.scope]:
            type1 = self.symbol_table[self.scope][tmp[1]]['type']
        else:
            type1 = self.symbol_table[0][tmp[1]]['type']
        print("type in name_or_procedure: " + type1)
        return type1


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
                self.write_error(
                    'parenthesis', '(', tmp[1], inspect.stack()[0][3])
                return

        self.argument_list()

        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])

    def argument_list(self):
        print('expanding argument list')
        self.expression()

        tmp = self.token.peek()
        print("val in argument list after expression "+str(tmp))
        if tmp[1] == ',':
            # consume the comma
            self.token.next()
            self.argument_list()


p = Parser()
