from numba.core.bytecode import *
from numba.core.interpreter import Interpreter
from numba.core.ir import *
from numba.core.ssa import reconstruct_ssa


# throws numba.core.errors.UnsupportedError  
def numba_ssa_ir(function):
    function_identity = FunctionIdentity.from_function(function)

    interpreter = Interpreter(function_identity)
    byte_code = ByteCode(function_identity)

    ir = interpreter.interpret(byte_code)
    reconstruct_ssa(ir)

    return ir
