from scanner import Scanner
import json
import inspect
import uuid
import sys
import logging

from llvmlite import ir
import llvmlite.binding as llvm
from ctypes import CFUNCTYPE, c_int64, c_int


llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

INTTYPE = ir.IntType(64)
FLOATTYPE = ir.DoubleType()
BOOLTYPE = ir.IntType(64)

logging.basicConfig(level=logging.ERROR)

def ARRAYTYPE(element, length):
    return ir.ArrayType(type_map[element], length)


def STRINGTYPE(length):
    return ir.ArrayType(ir.IntType(8), length)


type_map = {
    'integer': INTTYPE,
    'float': FLOATTYPE,
    'bool': BOOLTYPE,
    'string': STRINGTYPE(256),
    'enum': INTTYPE
}

cast_map = {
    'integer': int,
    'float': float,
    'bool': int
}

FALSE = ir.Constant(BOOLTYPE, 0)
TRUE = ir.Constant(BOOLTYPE, 1)
ZERO = ir.Constant(INTTYPE, 0)


class Iter():
    def __init__(self,f):
        self.scanner = Scanner(f)
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
    def __init__(self, f):

        self.token = Iter(f)

        self.symbol_table = [{}, {}]

        self.scope = 1

        self.builderStack = []
        self.funcStack = []

        llvm.load_library_permanently("./runtime/runtimelib.so")
        target = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine()

        backing_mod = llvm.parse_assembly("")
        engine = llvm.create_mcjit_compiler(backing_mod, target_machine)

        self.module = ir.Module(name="program")
        self.init_symbol_table()

        self.program()

        print(self.module)

        mod = llvm.parse_assembly(str(self.module))
        mod.verify()

        engine.add_module(mod)
        engine.finalize_object()

        main_func_ptr = engine.get_function_address("main_function")
        self.main_fn_fib = CFUNCTYPE(c_int64)(main_func_ptr)

        res = self.main_fn_fib()
        logging.debug("RES: "+str(res))

    def init_symbol_table(self):
        builtins = {
            'getbool': 'bool',
            'getinteger': 'integer',
            'getfloat': 'float',
            'getstring': 'integer',
            'putbool': 'bool',
            'putinteger': 'bool',
            'putfloat': 'bool',
            'putstring': 'bool',
            'sqrt': 'float',
            'strcomp': 'bool'
        }
        for key, val in builtins.items():
            self.add_entry(key, val, procedure=True, symbol_global=True)
            if key == "putstring":
                argtype = (ir.PointerType(type_map["string"]), )
            elif key.startswith('put'):
                argtype = (type_map[key.replace("put", "")], )#(ir.PointerType(type_map[key.replace("put", "")]), )
            elif key == "strcomp":
                type1 = ir.PointerType(type_map["string"])
                argtype = (type1, type1)
            elif key == "sqrt":
                argtype = (type_map["integer"], )#(ir.PointerType(type_map["float"]), )
            elif key == 'getstring':
                argtype = (ir.PointerType(type_map["string"]), )
            else:
                argtype = []

            logging.debug(argtype)
            fnty = ir.FunctionType(type_map[val], argtype)
            if key == 'sqrt':
                func = ir.Function(self.module, fnty, name='sqrtt')
            else:
                func = ir.Function(self.module, fnty, name=key)
            self.set_sym_entry(key, 'val', func)
            logging.debug(func)

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
            'global': symbol_global,
            'procedure': procedure,
            'val': val
        }
        if symbol_global:
            self.symbol_table[0][symbol_name] = data
        else:
            self.symbol_table[self.scope][symbol_name] = data
            if procedure:
                self.symbol_table[self.scope-1][symbol_name] = data

    def get_sym_entry(self, name):
        if name in self.symbol_table[self.scope]:
            return self.symbol_table[self.scope][name]
        elif name in self.symbol_table[0]:
            return self.symbol_table[0][name]
        else:
            return None

    def set_sym_entry(self, name, field, val):
        if name in self.symbol_table[self.scope]:
            self.symbol_table[self.scope][name][field] = val
        elif name in self.symbol_table[0]:
            self.symbol_table[0][name][field] = val
        else:
            self.symbol_error(name, inspect.stack()[0][3])

    def write_error(self, expected_type, expected_token, received_token, function):
        logging.error(json.dumps({'error': 'missing {}'.format(expected_type), 'details': "expected '{}', got '{}'".format(
            expected_token, received_token), 'lineno': Scanner.lineno, 'traceback': function}))

    def type_error(self, expected_type, received_type, function):
        logging.error(json.dumps({'error': 'type mismatch', 'details': "cannot resolve '{}' and '{}'".format(
            expected_type, received_type), 'lineno': Scanner.lineno, 'traceback': function}))

    def symbol_error(self, var_name, function):
        logging.error(json.dumps({'error': 'variable {} not defined'.format(
            var_name), 'lineno': Scanner.lineno, 'traceback': function}))
    
    def other_error(self, err, details, function):
        logging.error(json.dumps({'error': err, 'details': details, 'lineno': Scanner.lineno, 'traceback': function}))

    def program(self):
        logging.debug('expanding program')

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

        logging.debug(self.symbol_table)

    def program_header(self):
        logging.debug('expanding program header')
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
        logging.debug('expanding program body')

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
        logging.debug("MOVING ON TO PROGRAM CODE FINALLY")
        # Consume the begin
        tmp = self.token.next()

        # Move to next token
        tmp = self.token.peek()

        while tmp[1] != 'end':
            self.statement()
            tmp = self.token.next()
            logging.debug("Back in program body, tmp is "+str(tmp))
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
        logging.debug('expanding declaration')
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
            if symbol_bound:
                mem = self.builderStack[-1].alloca(
                    ARRAYTYPE(symbol_type, symbol_bound), name=symbol_name)
            else:
                mem = self.builderStack[-1].alloca(
                    type_map[symbol_type], name=symbol_name)
            
            if global_symbol:
                typ = ARRAYTYPE(symbol_type, symbol_bound) if symbol_bound else type_map[symbol_type]
                mem = ir.GlobalVariable(self.module, typ, symbol_name)
                mem.linkage = "internal"

            self.set_sym_entry(symbol_name, 'val', mem)
        elif tmp[1] == 'type':
            symbol_name, symbol_type = self.type_declaration()
            self.add_entry(symbol_name, symbol_type,
                           symbol_global=global_symbol)
        else:
            self.write_error(
                'declaration', '"procedure","variable", or "type"', tmp[1], inspect.stack()[0][3])
            return

    def procedure_declaration(self):
        logging.debug('expanding procedure declaration')
        self.symbol_table.append({})
        self.scope += 1

        plist = self.procedure_header()

        function_block = self.funcStack[-1].append_basic_block(
            name="function_entry")
        self.builderStack.append(ir.IRBuilder(function_block))
        # self.funcStack[-1]_args, = self.funcStack[-1].args

        for idx in range(len(plist)):
            param = plist[idx]
            param_name = param[0]
            param_val = self.get_sym_entry(param_name)['val']
            ptr = self.builderStack[-1].alloca(param[1], name=param_name)
            self.builderStack[-1].store(param_val, ptr)
            self.set_sym_entry(param_name, 'val', ptr)

        self.procedure_body()

        # for n in range(41):
        #     res = c_fn_fib(n)
        #     logging.debug(n, res)

        self.symbol_table.pop()
        self.scope -= 1

    def procedure_header(self):
        logging.debug('expanding procedure header')
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

        func = ir.FunctionType(type_map[symbol_type], types)
        fndef = ir.Function(self.module, func, name=str(uuid.uuid4()))
        self.funcStack.append(fndef)

        argslist = fndef.args
        for idx in range(len(plist)):
            param = plist[idx]
            param_name = param[0]
            param_val = argslist[idx]
            self.set_sym_entry(param_name, 'val', param_val)
        logging.debug(argslist)

        self.add_entry(symbol_name, symbol_type, procedure=True, val=fndef)
        return plist

    def parameter_list(self):
        logging.debug('expanding parameter list')
        name1, type1 = self.parameter()

        tmp = self.token.peek()

        if tmp[1] == ',':
            # consume it
            self.token.next()
            x = self.parameter_list()
            logging.debug(x)
            name2 = x[0][0]
            type2 = x[0][1]

            return [(name1, type1)]+[(name2, type2)]
        return [(name1, type1)]

    def parameter(self):
        logging.debug('expanding parameter')
        symbol_name, symbol_type, symbol_bound = self.variable_declaration()
        self.add_entry(symbol_name, symbol_type, symbol_bound=symbol_bound)
        logging.debug(symbol_name)
        return (symbol_name, type_map[symbol_type])

    def procedure_body(self):
        logging.debug('expanding procedure body')

        tmp = self.token.peek()
        logging.debug(tmp)
        while tmp[1] != 'begin':
            self.declaration()
            tmp = self.token.next()
            logging.debug(tmp)
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
        logging.debug("FOUND THE PROCEDURE BEGIN")

        tmp = self.token.peek()
        hasReturn = False
        while tmp[1] != 'end':
            if tmp[1] == 'return':
                hasReturn = True
            self.statement()
            tmp = self.token.next()
            if tmp[1] != ';':
                self.write_error('semicolon', ';',
                                 tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.peek()

        if not hasReturn:
            self.write_error('return', 'return', tmp[1], inspect.stack()[0][3])

        logging.debug("FOUND THE PROCEDURE END")
        # Now token is end, so consume it and read the next one
        self.token.next()
        tmp = self.token.next()
        if tmp[1] != 'procedure':
            self.write_error('end procedure', 'end procedure',
                             tmp[1], inspect.stack()[0][3])
            return
        self.builderStack.pop()
        self.funcStack.pop()
        logging.debug("RETURN CONTROL TO PROGRAM")

    def variable_declaration(self):
        logging.debug('expanding variable declaration')
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
        logging.debug('expanding type declaration')
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
        logging.debug('expanding type mark')
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
        logging.debug('expanding enum')
        tmp = self.token.next()
        if tmp[1] != '{':
            self.write_error('brace', '{', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>',
                             tmp[1], inspect.stack()[0][3])
            return

        ptr = self.builderStack[-1].alloca(INTTYPE, name=tmp[1])
        self.builderStack[-1].store(ir.Constant(INTTYPE, 0), ptr)
        self.add_entry(tmp[1], 'integer', val=ptr)

        tmp = self.token.next()

        count = 1
        while tmp[1] != '}':
            if tmp[1] != ',':
                self.write_error('comma', ',', tmp[1], inspect.stack()[0][3])
                return
            tmp = self.token.next()
            if tmp[0] != 'Identifier':
                self.write_error('identifier', '<identifier>',
                                 tmp[1], inspect.stack()[0][3])
                return

            ptr = self.builderStack[-1].alloca(INTTYPE, name=tmp[1])
            self.builderStack[-1].store(ir.Constant(INTTYPE, count), ptr)
            self.add_entry(tmp[1], 'integer', val=ptr)

            count += 1
            tmp = self.token.next()

    def bound(self):
        tmp = self.token.next()
        if tmp[0] != 'Digit':
            self.write_error('digit', '<digit>', tmp[1], inspect.stack()[0][3])
            return
        return int(tmp[1])

    def statement(self):
        logging.debug('expanding statement')
        tmp = self.token.peek()
        logging.debug(tmp)
        if tmp[1] == 'if':
            self.if_statement()
        elif tmp[1] == 'for':
            self.for_statement()
        elif tmp[1] == 'return':
            self.return_statement()
        else:
            self.assignment_statement()

    def return_statement(self):
        logging.debug('expanding return statement')
        tmp = self.token.next()
        if tmp[1] != 'return':
            self.write_error('return', 'return', tmp[1], inspect.stack()[0][3])
        val1, type1 = self.expression()
        logging.debug(val1)
        self.builderStack[-1].ret(val1)

    def if_statement(self):
        logging.debug('expanding if statement')
        tmp = self.token.next()
        if tmp[1] != 'if':
            self.write_error('if', 'if', tmp[1], inspect.stack()[0][3])
            return

        tmp = self.token.next()
        if tmp[1] != '(':
            self.write_error('parenthesis', '(', tmp[1], inspect.stack()[0][3])
            return

        condition, type2 = self.expression()
        logging.debug(condition)
        condition = self.builderStack[-1].icmp_signed("==", TRUE, condition)
        logging.debug(type2)
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
                    self.write_error('semicolon', ';',
                                     tmp[1], inspect.stack()[0][3])
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
                        logging.debug("matching semicolon in if_statement")
                        tmp = self.token.peek()

        # should be end now -- consume it
        tmp = self.token.next()
        logging.debug(tmp)
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

        logging.debug('expanding for statement')
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
        self.builderStack[-1].position_at_start(for_start_block)

        tmp = self.token.next()
        if tmp[1] != ';':
            self.write_error('semicolon', ';', tmp[1], inspect.stack()[0][3])
            return

        cond, type1 = self.expression()
        logging.debug(cond)
        cond = self.builderStack[-1].icmp_signed("==", TRUE, cond)
        logging.debug(cond)

        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])
            return
        logging.debug("here i am discarding the ) in for_statement")
        self.builderStack[-1].cbranch(cond, for_body_block, for_after_block)

        tmp = self.token.peek()
        while tmp[1] != 'end':
            self.builderStack[-1].position_at_end(for_body_block)
            logging.debug("In the while in for statement " + str(tmp))
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

        mem = self.get_sym_entry(for_var_name)['val']
        ptr = self.builderStack[-1].load(mem)

        for_var_val = self.builderStack[-1].add(ptr, ir.Constant(INTTYPE, 1))
        self.builderStack[-1].store(for_var_val, mem)

        self.builderStack[-1].branch(for_start_block)

        self.builderStack[-1].position_at_start(for_after_block)

    def assignment_statement(self):
        logging.debug('expanding assignment statement')
        var_name, type1, boundval = self.destination()

        tmp = self.token.next()
        logging.debug(tmp)
        if tmp[1] != ':=':
            self.write_error('assignment operator', ':=',
                             tmp[1], inspect.stack()[0][3])
            return

        sym_entry = self.get_sym_entry(var_name)
        logging.debug(sym_entry)
        val, type2 = self.expression()
        res = self.check_types(type1, type2)
        logging.debug('type in assignment_statement: '+res)
        if type1 != type2:
            self.other_error("illegal assignment", "assignment types must match exactly", inspect.stack()[0][3])
            return

        logging.debug(val)
        if res == 'bool':
            val = self.builderStack[-1].zext(val, type_map[res])

        mem = sym_entry['val']
        logging.debug("mem loc is")
        logging.debug(mem)
        if boundval:
            ptrInArray = self.builderStack[-1].gep(mem, [ZERO, boundval])
            self.builderStack[-1].store(val, ptrInArray)
        else:
            if not sym_entry['bound']:
                self.builderStack[-1].store(val, mem)
            else:
                if type(val) == list:
                    for i in range(len(val)):
                        ind = ir.Constant(INTTYPE, i)
                        ptrInArray = self.builderStack[-1].gep(mem, [ZERO, ind])
                        self.builderStack[-1].store(val[i], ptrInArray)
                else:
                    for i in range(sym_entry['bound']):
                        ind = ir.Constant(INTTYPE, i)
                        ptrInArray = self.builderStack[-1].gep(mem, [ZERO, ind])
                        self.builderStack[-1].store(val, ptrInArray)
        return var_name, val

    def destination(self):
        logging.debug('expanding destination')
        tmp = self.token.next()
        if tmp[0] != 'Identifier':
            self.write_error('identifier', '<identifier>',
                             tmp[1], inspect.stack()[0][3])
            return

        var_name = tmp[1]
        if var_name not in self.symbol_table[self.scope] and var_name not in self.symbol_table[0]:
            self.symbol_error(var_name, inspect.stack()[0][3])

        tmp = self.token.peek()
        boundval = None
        if tmp[1] == '[':
            # Consume it
            self.token.next()

            boundval, boundtype = self.expression()
            self.check_types('integer', boundtype)

            tmp = self.token.next()
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return

        type1 = self.symbol_table[self.scope][var_name]['type'] if var_name in self.symbol_table[
            self.scope] else self.symbol_table[0][var_name]['type']
        return var_name, type1, boundval

    def expression(self):
        logging.debug('expanding expression')
        tmp = self.token.peek()

        negate = False
        if tmp[1] == 'not':
            # Consume it
            tmp = self.token.next()
            negate = True

        val1, type1 = self.arithOp()
        logging.debug("val in expression after arithOp is "+str(val1) + " " + type1)

        tmp = self.token.peek()

        # acceptable
        if tmp[1] == '&' or tmp[1] == '|':
            # Consume &
            self.token.next()
            val2, type2 = self.expression()

            if type(val1) == list or type(val2) == list:
                self.other_error('illegal operation', 'logical operators not supported on arrays', inspect.stack()[0][3])
                return val1, type1

            res = self.check_types(type1, type2)
            if res == 'bool':
                #intermediate = self.builderStack[-1].add(val1, val2)
                if tmp[1] == "&":
                    # self.builderStack[-1].icmp_signed(
                    test = self.builderStack[-1].and_(val1, val2)
                    #cmpop="==", lhs=intermediate, rhs=ir.Constant(BOOLTYPE, 2))
                else:
                    # self.builderStack[-1].icmp_signed(
                    test = self.builderStack[-1].or_(val1, val2)
                    #cmpop="!=", lhs=intermediate, rhs=FALSE)
            else:
                if tmp[1] == "&":
                    test = self.builderStack[-1].and_(val1, val2)
                else:
                    test = self.builderStack[-1].or_(val1, val2)

            if negate:
                test = self.builderStack[-1].neg(test)
            return test, res
        else:
            if negate:
                val1 = self.builderStack[-1].neg(val1)
            return val1, type1

    def arithOp(self):
        logging.debug('expanding arithOp')
        val1, type1 = self.relation()
        logging.debug(type1)
        tmp = self.token.peek()
        logging.debug("value in arithop after relation is " + str(tmp))
        if tmp[1] == '+' or tmp[1] == '-':
            tmp = self.token.next()
            val2, type2 = self.arithOp()
            logging.debug(type2)
            res = self.check_types(type1, type2)

            if type(val1) == list and type(val2) == list:
                logging.debug("array IN ARITHOP")
                if len(val1) != len(val2):
                    self.other_error('illegal operation', 'cannot add arrays of different length', inspect.stack()[0][3])
                val = []
                for i in range(len(val1)):
                    if tmp[1] == '+':
                        val.append(self.builderStack[-1].add(val1[i], val2[i]))
                    else:
                        val.append(self.builderStack[-1].sub(val1[i], val2[i]))
            elif type(val1) == list:
                val = []
                for i in range(len(val1)):
                    if tmp[1] == '+':
                        val.append(self.builderStack[-1].add(val1[i], val2))
                    else:
                        val.append(self.builderStack[-1].sub(val1[i], val2))
            elif type(val2) == list:
                val = []
                for i in range(len(val2)):
                    if tmp[1] == '+':
                        val.append(self.builderStack[-1].add(val1, val2[i]))
                    else:
                        val.append(self.builderStack[-1].sub(val1, val2[i]))
            else:
                if tmp[1] == '+':
                    logging.debug("ADDING IN ARITHOP")
                    logging.debug(val1)
                    logging.debug(val2)
                    val = self.builderStack[-1].add(val1, val2)
                else:
                    val = self.builderStack[-1].sub(val1, val2)

            return val, res

        return val1, type1

    def relation(self):
        logging.debug('expanding relation')
        val1, type1 = self.term()
        logging.debug(type1)
        tmp = self.token.peek()
        logging.debug("value in relation after term is " + str(tmp))
        if tmp[1] in ['<', '<=', '>', '>=', '==', '!=']:
            tmp = self.token.next()
            val2, type2 = self.relation()
            logging.debug(type2)
            logging.debug(type1, type2)
            res = self.check_types(type1, type2)

            if type(val1) == list or type(val2) == list:
                self.other_error('illegal operation', 'relational operators not supported on arrays', inspect.stack()[0][3])
                return val1, type1

            logging.debug(res)
            if res != "string":
                logging.debug(val1, val2)
                if type1 == 'integer' and type2 == 'bool':
                    val1 = self.builderStack[-1].icmp_signed("!=", FALSE, val1)
                    val1 = self.builderStack[-1].zext(val1, INTTYPE)
                elif type1 == 'bool' and type2 == 'integer':
                    val2 = self.builderStack[-1].icmp_signed("!=", FALSE, val2)
                    val2 = self.builderStack[-1].zext(val2, INTTYPE)
                val = self.builderStack[-1].icmp_signed(tmp[1], val1, val2)
                val = self.builderStack[-1].zext(val, BOOLTYPE)
                logging.debug(val)
            else:
                if tmp[1] != "==" and tmp[1] != "!=":
                    self.other_error("invalid operation", "strings can only be compared", inspect.stack()[0][3])
                else:
                    ptr1 = self.builderStack[-1].alloca(type_map['string'])
                    ptr2 = self.builderStack[-1].alloca(type_map['string'])
                    self.builderStack[-1].store(val1, ptr1)
                    self.builderStack[-1].store(val2, ptr2)
                    strcomp = self.get_sym_entry('strcomp')['val']

                    v = self.builderStack[-1].call(strcomp, [ptr1, ptr2])
                    val = self.builderStack[-1].icmp_signed(tmp[1], v, TRUE)
                    val = self.builderStack[-1].zext(val, INTTYPE)
                    logging.debug("printing v and val: ")
                    logging.debug(v, val)

            return val, 'bool'
        return val1, type1

    def term(self):
        logging.debug('expanding term')
        val1, type1 = self.factor()

        tmp = self.token.peek()
        logging.debug("value in term after factor is " + str(tmp))
        if tmp[1] == '*' or tmp[1] == '/':
            tmp = self.token.next()
            val2, type2 = self.term()
            res = self.check_types(type1, type2)
            if type(val1) == 'list' and type(val2) == list:
                if len(val1) != len(val2):
                    self.other_error('illegal operation', 'cannot add arrays of different length', inspect.stack()[0][3])
                val = []
                for i in range(len(val1)):
                    if tmp[1] == "*":
                        val.append(self.builderStack[-1].mul(val1[i], val2[i]))
                    else:
                        val.append(self.builderStack[-1].sdiv(val1[i], val2[i]))
            elif type(val1) == list:
                val = []
                for i in range(len(val1)):
                    if tmp[1] == "*":
                        val.append(self.builderStack[-1].mul(val1[i], val2))
                    else:
                        val.append(self.builderStack[-1].sdiv(val1[i], val2))
            elif type(val2) == list:
                val = []
                for i in range(len(val1)):
                    if tmp[1] == "*":
                        val.append(self.builderStack[-1].mul(val1, val2[i]))
                    else:
                        val.append(self.builderStack[-1].sdiv(val1, val2[i]))
            else:
                val = self.builderStack[-1].mul(val1, val2)
            return val, res
        return val1, type1

    def factor(self):
        logging.debug('expanding factor')
        tmp = self.token.peek()
        logging.debug("in factor " + str(tmp))
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
            s = tmp[1][1:-1]
            s += "\0" + "0"*(256-len(s)-1)
            res = bytearray(s.encode())
            val = ir.Constant(STRINGTYPE(256), res)
            logging.debug('acceptable: string')

        elif tmp[1] == 'true' or tmp[1] == 'false':
            tmp = self.token.next()
            type1 = 'bool'
            val = FALSE if tmp[1] == 'false' else TRUE
            logging.debug('acceptable: bool')
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
                logging.debug('acceptable: negative digit')
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
                    logging.debug(tmp[1])
                    logging.debug("VAL IN FACTOR " + str(val))
            else:
                type1 = 'integer'
                val = ir.Constant(INTTYPE, int(tmp[1]))
            logging.debug('acceptable: digit')
        elif tmp[0] == 'Identifier':
            logging.debug('name or procedure call?')
            val, type1 = self.name_or_procedure()
        else:
            self.write_error('(, <string>, <bool>, -, <digit>, <identifier>',
                             '(, <string>, <bool>, -, <digit>, <identifier>', tmp[1], inspect.stack()[0][3])

        logging.debug("type in factor: "+type1)
        #logging.debug("symbol in factor: "+symbol)

        logging.debug("AT THE END OF FACTOR, val= ")
        logging.debug(val)
        return val, type1

    def name_or_procedure(self):
        logging.debug('expanding name or procedure')
        # consume the identifier
        tmp = self.token.next()
        if tmp[1] not in self.symbol_table[self.scope] and tmp[1] not in self.symbol_table[0]:
            self.symbol_error(tmp[1], inspect.stack()[0][3])
        logging.debug(tmp)
        tmp2 = self.token.peek()
        if tmp2[1] == '(':
            ptr = self.procedure_call(tmp)
        else:
            boundval = self.name()
            sym = self.get_sym_entry(tmp[1])
            logging.debug(sym)
            val = sym['val']
            if type(val) == ir.values.Argument:
                ptr = val
            else:
                if boundval:
                    logging.debug("PRINTING BOUNDVAL: " + str(boundval))
                    logging.debug(val)
                    ptrInArray = self.builderStack[-1].gep(
                        val, [ZERO, boundval])
                    ptr = self.builderStack[-1].load(ptrInArray)
                elif sym['bound']:
                    ptr = []
                    for i in range(sym['bound']):
                        ptrInArray = self.builderStack[-1].gep(
                            val, [ZERO, ir.Constant(INTTYPE, i)])
                        ptr.append(self.builderStack[-1].load(ptrInArray))                    
                else:
                    ptr = self.builderStack[-1].load(val)

        type1 = self.get_sym_entry(tmp[1])['type']
        if tmp[1] == 'getstring':
            type1 = 'string'
        logging.debug("type in name_or_procedure: " + type1)
       # logging.debug("val in name_or_procedure: " + str(val))
        return ptr, type1

    def name(self):
        logging.debug('expanding name')
        tmp = self.token.peek()

        boundval = None
        if tmp[1] == '[':
            tmp = self.token.next()
            boundval, type1 = self.expression()
            self.check_types('integer', type1)
            tmp = self.token.next()
            if tmp[1] != ']':
                self.write_error('bracket', ']', tmp[1], inspect.stack()[0][3])
                return
        return boundval

    def procedure_call(self, fn):
        logging.debug('expanding procedure call')
        # consume the (
        tmp = self.token.next()
        logging.debug("in expand procedure call: "+str(tmp))
        if tmp[1] != '(':
                self.write_error(
                    'parenthesis', '(', tmp[1], inspect.stack()[0][3])
                return

        tmp = self.token.peek()
        logging.debug(fn)
        arglist = []
        if tmp[1] != ')':
            args = self.argument_list()
            logging.debug(args)
            logging.debug("arglist is: ")
            for arg in args:
                logging.debug(arg)
                argval = arg[0]
                argtype = arg[1]
                if argtype == 'string':
                    ptr = self.builderStack[-1].alloca(type_map[argtype])
                    self.builderStack[-1].store(argval, ptr)
                    arglist.append(ptr)
                else:
                    arglist.append(argval)
        
        logging.debug(arglist)
        tmp = self.token.next()
        if tmp[1] != ')':
            self.write_error('parenthesis', ')', tmp[1], inspect.stack()[0][3])

        logging.debug("Here I am right before the die")
        fncall = self.get_sym_entry(fn[1])['val']

        if fn[1] == "getstring":
            s = "\0"+"0"*255
            logging.debug(s)
            res = bytearray(s.encode())
            val = ir.Constant(STRINGTYPE(256), res)
            ptr = self.builderStack[-1].alloca(type_map['string'])
            #self.builderStack[-1].store(val, ptr)
            arglist.append(ptr)
            logging.debug(fncall, arglist)
            retval = self.builderStack[-1].call(fncall, arglist)
            logging.debug("and here: " + str(retval))
            logging.debug(ptr)
            asdf = self.builderStack[-1].load(ptr)
            logging.debug(asdf)
            return asdf
        else:
            logging.debug(fncall, arglist)
            retval = self.builderStack[-1].call(fncall, arglist)
            logging.debug("and here: " +  str(retval))
            return retval

    def argument_list(self):
        logging.debug('expanding argument list')
        val1, type1 = self.expression()

        tmp = self.token.peek()
        logging.debug("val in argument list after expression "+str(tmp))
        if tmp[1] == ',':
            # consume the comma
            self.token.next()
            val2, type2 = self.argument_list()[0]
            return [(val1, type1)]+ [(val2, type2)]

        return [(val1, type1)]

try:
    f = sys.argv[1]
    p = Parser(f)
except Exception as e:
    logging.error("internal error")
    logging.debug(str(e))
    #print(e)
