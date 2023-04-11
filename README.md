# Type Inference for Python

All source code for CPSC 539B class project "Type Inference for Python", including code for extracting typing information from typeshed, structural subtyping calculation, and a Jupyter notebook that runs our type inference procedure on the `shell_sort` example:

```python
def shell_sort(collection):
    # Marcin Ciura's gap sequence
    gaps = [701, 301, 132, 57, 23, 10, 4, 1]
    for gap in gaps:
        i = gap
        while i < len(collection):
            temp = collection[i]
            j = i
            while j >= gap and collection[j - gap] > temp:
                collection[j] = collection[j - gap]
                j -= gap
            collection[j] = temp
            i += 1
    return collection
```

## Requirements

- Jupyter Notebook, with a Python 3 kernel and the following extensions:
  - `attrs`
  - `disjoint-set`
  - `more-itertools`
  - `networkx`
  - `numba`
  - `ordered-set`
  - [`settrie`](https://github.com/mmihaltz/pysettrie)
  - `sortedcontainers`
  - `typeshed-client`

## Code Organization

- `type_annotation.py`: Contains the definitions of our type annotations used to represent type annotations in `typeshed`: `TypeVariable`, `ConcreteClass`, `Subscription`, `GlobalFunction`, and `Union` (all hashable), as well as functions to manipulate them.
- `class_definition.py`, `function_definition.py`: Contains the definitions of the classes `ClassDefinition` and `FunctionDefinition`, which are used to represent class definitions and function definitions looked up from `typeshed`, as well as functions to manipulate them.
- `look_up.py`: Contains functions to look up `ClassDefinition`'s and `FunctionDefinition`'s from `typeshed` (performing extensive AST parsing in the process): `look_up_class` and `look_up_global_function`. Example presented at the head of the file.
- `subtyping.py`: Contains a function `type_annotation_subtyping` that performs *structural subtyping* calculation between two type annotations, as well as figures out what each `TypeVariable` in the two type annotations should be. Example presented at the head of the file.
- `numba_ssa_ir.py`: Lowers a Python function to Numba SSA IR.
- `type_inference_for_python.ipynb`: A Jupyter notebook that runs our type inference procedure on the `shell_sort` example. Includes representations for typing constraints, functions for updating typing constraints, functions for handling typing rules for Numba IR expressions, and functions for inferring types for variables from typing constraints.

## Replication Instructions

Run `type_inference_for_python.ipynb`.
