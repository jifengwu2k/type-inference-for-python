def numba_ssa_ir_instructions(ir):
    return [inst for k, block in ir.blocks.items() for inst in block.body]
