from llvmlite import ir
import llvmlite.binding as llvm
from ctypes import CFUNCTYPE, c_int64, c_int8


llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()


# def fibonacci(n):
#     if n <= 1:
#         return 1
#     return fibonacci(n - 1) + fibonacci(n - 2)

int_type = ir.IntType(64)
bool_type = ir.IntType(64)

FALSE = ir.Constant(bool_type, 0)
TRUE = ir.Constant(bool_type, 1)

# function of return type int_type, taking
# arguments [int_type]
fn = ir.FunctionType(int_type, [int_type])

module = ir.Module(name="fib_example")

fn_fib = ir.Function(module, fn, name="fn_fib")
fn_fib_block = fn_fib.append_basic_block(name="fn_fib_entry")

builder = ir.IRBuilder(fn_fib_block)
fn_fib_n, = fn_fib.args

const_1 = ir.Constant(int_type, 1)
const_2 = ir.Constant(int_type, 2)

t1 = ir.Constant(bool_type, 0)
t2 = ir.Constant(bool_type, 0)
test1 = builder.and_(t1,t2)
#lhs = builder.add(t1,t2)
test = builder.icmp_signed(cmpop="==", lhs=test1, rhs=TRUE)

fn_fib_n_le_1 = builder.icmp_signed(cmpop="<=", lhs=fn_fib_n, rhs=const_1)

with builder.if_then(test):
    builder.ret(const_1)

fn_fib_n_minus_1 = builder.sub(fn_fib_n, const_1)
fn_fib_n_minus_2 = builder.sub(fn_fib_n, const_2)

call_fn_fib_n_minus_1 = builder.call(fn_fib, [fn_fib_n_minus_1])
call_fn_fib_n_minus_2 = builder.call(fn_fib, [fn_fib_n_minus_2])

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
c_fn_fib = CFUNCTYPE(c_int64, c_int64)(func_ptr)

for n in range(41):
    res = c_fn_fib(n)
    print(n, res)