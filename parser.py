from scanproto2 import Scanner
import json
import inspect
import uuid

from llvmlite import ir
import llvmlite.binding as llvm
from ctypes import CFUNCTYPE, c_int64, c_int


llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

INTTYPE = ir.IntType(64)
FLOATTYPE = ir.FloatType()
BOOLTYPE = ir.IntType(64)


def ARRAYTYPE(element, length):
    return ir.ArrayType(type_map[element], length)


def STRINGTYPE(length):
    return ir.ArrayType(ir.IntType(8), length)


type_map = {
    'integer': INTTYPE,
    'float': FLOATTYPE,
    'bool': BOOLTYPE,
    'string': STRINGTYPE,
}

cast_map = {
    'integer': int,
    'float': float,
    'bool': bool
}

FALSE = ir.Constant(BOOLTYPE, 0)
TRUE = ir.Constant(BOOLTYPE, 1)


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

        self.builderStack = []
        self.funcStack = []

        self.program()


        print(self.module)

        target = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine()

        backing_mod = llvm.parse_assembly("")
        engine = llvm.create_mcjit_compiler(backing_mod, target_machine)

        mod = llvm.parse_assembly(str(self.module))
        mod.verify()

        engine.add_module(mod)
        engine.finalize_object()

        main_func_ptr = engine.get_function_address("main_function")
        self.main_fn_fib = CFUNCTYPE(c_int64)(main_func_ptr)

        # res = self.main_fn_fib()
        # print("RES: "+str(res))


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

    def add_entry(self, symbol_name, symbol_type, symbol_bound=None, symbol_global=False, procedure=False, val=None):
        data = {
            'type': symbol_type,
            'bound': symbol_bound,
            'procedure': procedure,
            'val': val
        }
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

        self.module = ir.Module(name="program")
        main_func = ir.FunctionType(INTTYPE, [])
        self.main_function = ir.Function(
            self.module, main_func, name="main_function")
        self.funcStack.append(self.main_function)
        
        self.main_block = self.main_function.append_basic_block(
            name="main_entry")
        self.main_builder = ir.IRBuilder(self.main_block)
        self.builderStack.append(self.main_builder)

        self.program_header()
        self.program_body()

        self.main_builder.ret(ir.Constant(INTTYPE, 1))

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

        function_block = self.funcStack[-1].append_basic_block(
            name="function_entry")
        self.builderStack.append(ir.IRBuilder(function_block))
        # self.funcStack[-1]_args, = self.funcStack[-1].args

        self.procedure_body()

        # for n in range(41):
        #     res = c_fn_fib(n)
        #     print(n, res)

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

        tmp = self.token.peek()
        types = []
        plist = []
        if tmp[1] != ")":
            plist = self.parameter_list()
            types = [x[1] for x in plist]

        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return

        func = ir.FunctionType(INTTYPE, types)
        fndef = ir.Function(self.module, func, name=str(uuid.uuid4()) )
        self.funcStack.append(fndef)

        argslist = fndef.args
        for idx in range(len(plist)):
            param = plist[idx]
            param_name = param[0]
            param_val = argslist[idx]
            if param_name in self.symbol_table[self.scope]:
                self.symbol_table[self.scope][param_name]['val'] = param_val
            else:
                self.symbol_table[0][param_name]['val'] = param_val
        print(argslist)
        
        self.add_entry(symbol_name, symbol_type, procedure=True, val=fndef)

    def parameter_list(self):
        print('expanding parameter list')
        name1, type1 = self.parameter()
    
        tmp = self.token.peek()

        if tmp[1] == ',':
            # consume it
            self.token.next()
            name2, type2 = self.parameter_list()
        
            return [(name1,type1), (name2,type2)]
        return [(name1,type1)]

    def parameter(self):
        print('expanding parameter')
        symbol_name, symbol_type, symbol_bound = self.variable_declaration()
        self.add_entry(symbol_name, symbol_type, symbol_bound=symbol_bound)
        print(symbol_name)
        return (symbol_name, type_map[symbol_type])

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
        self.builderStack.pop()
        self.funcStack.pop()
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
        val1,type1 = self.expression()
        print(val1)
        self.builderStack[-1].ret(val1)

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

        condition, type2 = self.expression()
        res = self.check_types('bool', type2)

        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[1] != 'then':
            self.write_error('then', 'then', tmp[1], inspect.stack()[0][3])
            return
    
        with self.builderStack[-1].if_else(condition) as (then, otherwise):
            with then:
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
            with otherwise:
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
        for_start_block = self.builderStack[-1].append_basic_block("for_start")
        for_body_block = self.builderStack[-1].append_basic_block("for_body")
        for_after_block = self.builderStack[-1].append_basic_block("for_after")
        
        print('expanding for statement')
        tmp = self.token.next()
        if tmp[1] != 'for':
            self.write_error('for', 'for', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[1] != '(':
            self.write_error('parenthesis', '(', tmp[1], inspect.stack()[0][3])
            return

        for_var_name, for_var_val = self.assignment_statement()
        self.builderStack[-1].branch(for_start_block)
        self.builderStack[-1].position_at_end(for_start_block)

        tmp = self.token.next()
        if tmp[1] != ';':
            self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
            return

        cond, type1 = self.expression()
        print(cond)

        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return
        print("here i am discarding the ) in for_statement")
        self.builderStack[-1].cbranch(cond, for_body_block, for_after_block)

        tmp = self.token.peek()
        while tmp[1] != 'end':
            self.builderStack[-1].position_at_start(for_body_block)
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
        
        for_var_val = self.builderStack[-1].add(for_var_val, ir.Constant(INTTYPE, 1))
        if for_var_name in self.symbol_table[0]:
            self.symbol_table[0][for_var_name]['val'] = for_var_val
        else:
            self.symbol_table[self.scope][for_var_name]['val'] = for_var_val

        self.builderStack[-1].branch(for_start_block)

        self.builderStack[-1].position_at_start(for_after_block)


    def assignment_statement(self):
        print('expanding assignment statement')
        var_name, type1 = self.destination()

        tmp = self.token.next()

        if tmp[1] != ':=':
            self.write_error('assignment operator', ':=',
                             tmp[1], inspect.stack()[0][3])
            return

        val, type2 = self.expression()
        res = self.check_types(type1, type2)
        print('type in assignment_statement: '+res)

        print("Value in assignment statement")
        print(val)
        if var_name in self.symbol_table[0]:
            self.symbol_table[0][var_name]['val'] = val
        else:
            self.symbol_table[self.scope][var_name]['val'] = val
        return var_name, val

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

        type1 = self.symbol_table[self.scope][var_name]['type'] if var_name in self.symbol_table[
            self.scope] else self.symbol_table[0][var_name]['type']
        return var_name, type1

    def expression(self):
        print('expanding expression')
        tmp = self.token.peek()

        negate = False
        if tmp[1] == 'not':
            # Consume it
            tmp = self.token.next()
            negate = True

        val1, type1 = self.arithOp()

        tmp = self.token.peek()

        # acceptable
        if tmp[1] == '&' or tmp[1] == '|':
            # Consume &
            self.token.next()
            val2, type2 = self.expression()
            res = self.check_types(type1, type2)
            if res == 'bool':
                #intermediate = self.builderStack[-1].add(val1, val2)
                if tmp[1] == "&":
                    test = self.builderStack[-1].and_(val1,val2)#self.builderStack[-1].icmp_signed(
                        #cmpop="==", lhs=intermediate, rhs=ir.Constant(BOOLTYPE, 2))
                else:
                    test = self.builderStack[-1].or_(val1, val2)#self.builderStack[-1].icmp_signed(
                        #cmpop="!=", lhs=intermediate, rhs=FALSE)
            else:
                if tmp[1] == "&":
                    test = self.builderStack[-1].and_(val1, val2)
                else:
                    test = self.builderStack[-1].or_(val1, val2)

            return test, res
        else:
            return val1, type1

    def arithOp(self):
        print('expanding arithOp')
        val1, type1 = self.relation()

        tmp = self.token.peek()
        print("value in arithop after relation is " + str(tmp))
        if tmp[1] == '+' or tmp[1] == '-':
            tmp = self.token.next()
            val2, type2 = self.arithOp()
            res = self.check_types(type1, type2)
            if tmp[1] == '+':
                print("ADDING IN ARITHOP")
                print(val1)
                print(val2)
                val = self.builderStack[-1].add(val1, val2)
            else:
                val = self.builderStack[-1].sub(val1, val2)
            return val, res

        return val1, type1

    def relation(self):
        print('expanding relation')
        val1, type1 = self.term()

        tmp = self.token.peek()
        print("value in relation after term is " + str(tmp))
        if tmp[1] in ['<', '<=', '>', '>=', '==', '!=']:
            tmp = self.token.next()
            val2, type2 = self.relation()
            res = self.check_types(type1, type2)
            val = self.builderStack[-1].icmp_signed(tmp[1], val1, val2)
            return val, res
        return val1, type1

    def term(self):
        print('expanding term')
        val1, type1 = self.factor()

        tmp = self.token.peek()
        print("value in term after factor is " + str(tmp))
        if tmp[1] == '*' or tmp[1] == '/':
            tmp = self.token.next()
            val2, type2 = self.term()
            res = self.check_types(type1, type2)
            if tmp[1] == '*':
                val = self.builderStack[-1].mul(val1, val2)
            else:
                val = self.builderStack[-1].sdiv(val1, val2)
            return val, res
        return val1, type1

    def factor(self):
        print('expanding factor')
        tmp = self.token.peek()
        print("in factor " + str(tmp))
        if tmp[1] == '(':
            self.token.next()
            val, type1 = self.expression()
            tmp = self.token.next()
            if tmp[1] != ')':
                self.write_error('parenthesis', ')',
                                 tmp[1], inspect.stack()[0][3])
        elif tmp[0] == 'String':
            tmp = self.token.next()
            type1 = 'string'
            #TODO: Fix this
            val = ir.Constant(INTTYPE, 1)
            print('acceptable: string')
        elif tmp[1] == 'true' or tmp[1] == 'false':
            tmp = self.token.next()
            type1 = 'bool'
            val = FALSE if tmp[1] == 'false' else TRUE
            print('acceptable: bool')
        elif tmp[1] == '-':
            tmp = self.token.next()

            tmp = self.token.peek()
            if tmp[0] == 'Digit':
                symbol = self.token.next()[1]
                if '.' in tmp[1]:
                    type1 = 'float'
                    val = ir.Constant(FLOATTYPE, -float(tmp[1]))
                else:
                    type1 = 'integer'
                    val = ir.Constant(INTTYPE, -int(tmp[1]))
                print('acceptable: negative digit')
            elif tmp[0] == 'Identifier':
                symbol, type1 = self.name_or_procedure()
                val = self.builderStack[-1].neg(symbol)
            else:
                self.write_error('digit or identifier',
                                 '<digit> or <identifier>', tmp[1], inspect.stack()[0][3])
                return
        elif tmp[0] == 'Digit':
            symbol = self.token.next()[1]
            if '.' in tmp[1]:
                    type1 = 'float'
                    val = ir.Constant(FLOATTYPE, float(tmp[1]))
            else:
                type1 = 'integer'
                val = ir.Constant(INTTYPE, int(tmp[1]))
            print('acceptable: digit')
        elif tmp[0] == 'Identifier':
            print('name or procedure call?')
            val, type1 = self.name_or_procedure()
        else:
            self.write_error('(, <string>, <bool>, -, <digit>, <identifier>',
                             '(, <string>, <bool>, -, <digit>, <identifier>', tmp[1], inspect.stack()[0][3])

        print("type in factor: "+type1)
        #print("symbol in factor: "+symbol)

        print("AT THE END OF FACTOR, val= ")
        print(val)
        return val, type1

    def name_or_procedure(self):
        print('expanding name or procedure')
        # consume the identifier
        tmp = self.token.next()
        if tmp[1] not in self.symbol_table[self.scope] and tmp[1] not in self.symbol_table[0]:
            self.symbol_error(tmp[1], inspect.stack()[0][3])

        tmp2 = self.token.peek()
        if tmp2[1] == '(':
            val = self.procedure_call(tmp)
        else:
            self.name()
            if tmp[1] in self.symbol_table[self.scope]:
                val = self.symbol_table[self.scope][tmp[1]]['val']
                print(self.symbol_table[self.scope][tmp[1]])
            else:
                val = self.symbol_table[0][tmp[1]]['val']
                print(self.symbol_table[0][tmp[1]])

        if tmp[1] in self.symbol_table[self.scope]:
            type1 = self.symbol_table[self.scope][tmp[1]]['type']
        else:
            type1 = self.symbol_table[0][tmp[1]]['type']

        print("type in name_or_procedure: " + type1)
       # print("val in name_or_procedure: " + str(val))
        return val, type1

    def name(self):
        print('expanding name')
        tmp = self.token.peek()

        if tmp[1] == '[':
            self.expression()
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return

    def procedure_call(self, fn):
        print('expanding procedure call')
        # consume the (
        tmp = self.token.next()
        print("in expand procedure call: ", tmp)
        if tmp[1] != '(':
                self.write_error(
                    'parenthesis', '(', tmp[1], inspect.stack()[0][3])
                return

        tmp = self.token.peek()
        arglist = []
        if tmp[1] != ')':
            args = self.argument_list()
            #arglist = [ir.Constant(type_map[arg[1]], cast_map[arg[1]](arg[0])) for arg in args]
            arglist = [arg[0] for arg in args]

        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])

        print("Here I am right before the die")
        if fn[1] in self.symbol_table[self.scope]:
            fncall = self.symbol_table[self.scope][fn[1]]['val']
        else:
            fncall = self.symbol_table[0][fn[1]]['val']
        
        self.retval = self.builderStack[-1].call(fncall, arglist)
        return self.retval

    def argument_list(self):
        print('expanding argument list')
        val1, type1 = self.expression()

        tmp = self.token.peek()
        print("val in argument list after expression "+str(tmp))
        if tmp[1] == ',':
            # consume the comma
            self.token.next()
            val2, type2 = self.argument_list()
            return [(val1, type1), (val2, type2)]

        return [(val1, type1)]


p = Parser()
