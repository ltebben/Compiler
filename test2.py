from llvmlite import ir
import llvmlite.binding as llvm
from ctypes import CFUNCTYPE, c_int64, c_int8, c_char


llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()


# def fibonacci(n):
#     if n <= 1:
#         return 1
#     return fibonacci(n - 1) + fibonacci(n - 2)

int_type = ir.IntType(64)
bool_type = ir.IntType(64)
string_type = ir.ArrayType(ir.IntType(8), 256)

FALSE = ir.Constant(bool_type, 0)
TRUE = ir.Constant(bool_type, 1)

# function of return type int_type, taking
# arguments [int_type]
fn = ir.FunctionType(int_type, [string_type])

module = ir.Module(name="fib_example")

fn_fib = ir.Function(module, fn, name="fn_fib")
fn_fib_block = fn_fib.append_basic_block(name="fn_fib_entry")

builder = ir.IRBuilder(fn_fib_block)
fn_fib_n, = fn_fib.args
print(fn_fib.args)

const_1 = ir.Constant(int_type, 1)
const_2 = ir.Constant(int_type, 2)

s = "string test"
s += "\0" + "0"*(256-len(s)-1)
print(len(s))
print(s)
res = bytearray(s.encode())
val = ir.Constant(string_type, res)
mem = builder.alloca(string_type, name='string')            
builder.store(val, mem)
v2 = builder.load(mem)
print(v2)

call_fn_fib_n_minus_1 = builder.call(fn_fib, [v2])
call_fn_fib_n_minus_2 = builder.call(fn_fib, [v2])

fn_fib_res = builder.add(call_fn_fib_n_minus_1, call_fn_fib_n_minus_2)
builder.ret(fn_fib_res)

print(module)

target = llvm.Target.from_default_triple()
target_machine = target.create_target_machine()

backing_mod = llvm.parse_assembly("")
engine = llvm.create_mcjit_compiler(backing_mod, target_machine)

mod = llvm.parse_assembly(str(module))
mod.verify()

engine.add_module(mod)
engine.finalize_object()

func_ptr = engine.get_function_address("fn_fib")
c_fn_fib = CFUNCTYPE(c_int64, c_char)(func_ptr)

for n in range(41):
    p = str(n)
    res = c_fn_fib(p)
    print(n, res)