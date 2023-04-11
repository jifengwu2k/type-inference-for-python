"""
not subtype -> False, empty nx.DiGraph
conditional subtype -> True, non-empty nx.DiGraph
unconditional subtype -> True, empty nx.DiGraph

from type_annotation import *
from subtyping import *
t1 = TypeVariable()
t2 = TypeVariable()

------

retval = type_annotation_subtyping(Subscription(ConcreteClass('builtins', 'dict'), (t1, t2)), Subscription(ConcreteClass('builtins', 'dict'), (ConcreteClass('builtins', 'int'),ConcreteClass('builtins', 'str'))))

In [40]: retval[0]
Out[40]: True

In [41]: list(retval[1].successors(t1))
Out[41]: 
[ConcreteClass(module_name='builtins', class_name='int'),
 (ConcreteClass(module_name='builtins', class_name='int'),
  ConcreteClass(module_name='builtins', class_name='NoneType'))]

In [42]: list(retval[1].successors(t2))
Out[42]: 
[ConcreteClass(module_name='builtins', class_name='str'),
 (ConcreteClass(module_name='builtins', class_name='str'),
  ConcreteClass(module_name='builtins', class_name='NoneType'))]
  
------

retval = type_annotation_subtyping(Subscription(ConcreteClass('builtins', 'dict'), (t1, ConcreteClass('builtins', 'int'))), Subscription(ConcreteClass('builtins', 'dict'), (ConcreteClass('builtins', 'int'),ConcreteClass('builtins', 'str'))))

In [44]: retval[0]
Out[44]: False

In [45]: retval[1].edges
Out[45]: OutEdgeView([])

------

retval = type_annotation_subtyping(Subscription(ConcreteClass('builtins', 'dict'), (t1, ConcreteClass('builtins', 'int'))), Subscription(ConcreteClass('builtins', 'dict'), (ConcreteClass('builtins', 'str'), t2)))

In [47]: retval[0]
Out[47]: True

In [48]: list(retval[1].successors(t1))
Out[48]: 
[ConcreteClass(module_name='builtins', class_name='str'),
 (ConcreteClass(module_name='builtins', class_name='str'),
  ConcreteClass(module_name='builtins', class_name='NoneType'))]

In [49]: list(retval[1].predecessors(t2))
Out[49]: 
[ConcreteClass(module_name='builtins', class_name='int'),
 ConcreteClass(module_name='builtins', class_name='NoneType')]
 
------

retval = type_annotation_subtyping(ConcreteClass('builtins', 'bytearray'), Subscription(ConcreteClass('typing', 'Iterable'), (t1,)))

In [36]: retval[0]
Out[36]: True

In [38]: list(retval[1].predecessors(t1))
Out[38]: [ConcreteClass(module_name='builtins', class_name='int')]
"""

import importlib
import sys

import networkx as nx

from class_definition import ClassDefinition, instantiate_type_variables_in_class_definition
from look_up import look_up_class
from function_definition import FunctionDefinition
from type_annotation import *


def resolve_runtime_class_or_none(concrete_class, indent_level=0):
    indent = '    ' * indent_level
    
    print(indent, f'resolve_runtime_class_or_none {concrete_class}', file=sys.stderr)
    
    module_name = concrete_class.module_name
    class_name = concrete_class.class_name
    
    if module_name in ('typing', 'typing_extensions', 'collections.abc', '_collections_abc'):
        print(indent, 'the runtime class only serves typing purposes and would not have the information we want', file=sys.stderr)
        return None
    else:
        try:
            module = importlib.import_module(concrete_class.module_name)
            runtime_class = getattr(module, concrete_class.class_name)
            return runtime_class
        except (ModuleNotFoundError, AttributeError) as e:
            print(indent, type(e).__name__, str(e), file=sys.stderr)
            return None


def class_definition_subtyping(
    first_class_type_annotation_of_self_or_cls,
    first_class_definition: ClassDefinition,
    second_class_type_annotation_of_self_or_cls,
    second_class_definition: ClassDefinition,
    indent_level=0
) -> bool:
    indent = '    ' * indent_level

    print(indent, f'class_definition_subtyping {first_class_type_annotation_of_self_or_cls} {second_class_type_annotation_of_self_or_cls}', file=sys.stderr)
    
    type_variable_subtyping_digraph = nx.DiGraph()

    is_equal = lambda first_type_annotation, second_type_annotation: (first_type_annotation == second_type_annotation) or (first_type_annotation == first_class_type_annotation_of_self_or_cls and second_type_annotation == second_class_type_annotation_of_self_or_cls)
    
    for second_class_method_name, second_class_method_list in second_class_definition.method_name_to_method_list_dict.items():
        if second_class_method_name not in first_class_definition.method_name_to_method_list_dict:
            print(indent, f'{second_class_method_name} not in {first_class_definition.method_name_to_method_list_dict.keys()}', file=sys.stderr)
            return False, nx.DiGraph()
        else:
            first_class_method_list = first_class_definition.method_name_to_method_list_dict[second_class_method_name]
            
            # assert len(first_class_method_list) == 1 and len(second_class_method_list) == 1
            
            first_class_method = first_class_method_list[0]
            second_class_method = second_class_method_list[0]

            result_, type_variable_subtyping_digraph_ = function_definition_subtyping(first_class_method, second_class_method, indent_level + 1, is_equal=is_equal, is_method=True)
            if not result_:
                print(indent, f'not function_definition_subtyping({first_class_method}, {second_class_method})', file=sys.stderr)
                return False, nx.DiGraph()
            else:
                type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
    
    for second_class_staticmethod_name, second_class_staticmethod_list in second_class_definition.staticmethod_name_to_staticmethod_list_dict.items():
        if second_class_staticmethod_name not in first_class_definition.staticmethod_name_to_staticmethod_list_dict:
            print(indent, f'{second_class_staticmethod_name} not in {first_class_definition.staticmethod_name_to_staticmethod_list_dict.keys()}', file=sys.stderr)
            return False, nx.DiGraph()
        else:
            first_class_staticmethod_list = first_class_definition.staticmethod_name_to_staticmethod_list_dict[second_class_staticmethod_name]
            
            # assert len(first_class_staticmethod_list) == 1 and len(second_class_staticmethod_list) == 1
            
            first_class_staticmethod = first_class_staticmethod_list[0]
            second_class_staticmethod = second_class_staticmethod_list[0]

            result_, type_variable_subtyping_digraph_ = function_definition_subtyping(first_class_staticmethod, second_class_staticmethod, indent_level + 1, is_equal=is_equal)
            if not result_:
                print(indent, f'not function_definition_subtyping({first_class_staticmethod}, {second_class_staticmethod})', file=sys.stderr)
                return False, nx.DiGraph()
            else:
                type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
    
    for second_class_property_name, second_class_property_type_annotation in second_class_definition.property_name_to_property_type_annotation_dict.items():
        if second_class_property_name not in first_class_definition.property_name_to_property_type_annotation_dict:
            print(indent, f'{second_class_property_name} not in {first_class_definition.property_name_to_property_type_annotation_dict.keys}', file=sys.stderr)
            return False
        else:
            first_class_property_type_annotation = first_class_definition.property_name_to_property_type_annotation_dict[second_class_property_name]

            result_, type_variable_subtyping_digraph_ = type_annotation_subtyping(first_class_property_type_annotation, second_class_property_type_annotation, indent_level + 1, is_equal=is_equal)
            if not result_:
                print(indent, f'not type_annotation_subtyping({first_class_property_type_annotation}, {second_class_property_type_annotation})', file=sys.stderr)
                return False, nx.DiGraph()
            else:
                type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
    
    return True, type_variable_subtyping_digraph


def function_definition_subtyping(
    first_function_definition: FunctionDefinition,
    second_function_definition: FunctionDefinition,
    indent_level=0,
    *,
    is_equal=lambda first_type_annotation, second_type_annotation: first_type_annotation == second_type_annotation,
    is_method=False
) -> bool:
    indent = '    ' * indent_level

    print(indent, f'function_definition_subtyping {first_function_definition} {second_function_definition}', file=sys.stderr)
    
    type_variable_subtyping_digraph = nx.DiGraph()

    for (
        first_function_definition_parameter_type_annotation, 
        second_function_definition_parameter_type_annotation
    ) in zip(
        first_function_definition.parameter_type_annotation_list[1:] if is_method else first_function_definition.parameter_type_annotation_list,
        second_function_definition.parameter_type_annotation_list[1:] if is_method else second_function_definition.parameter_type_annotation_list
    ):
        result_, type_variable_subtyping_digraph_ = type_annotation_subtyping(
            second_function_definition_parameter_type_annotation,
            first_function_definition_parameter_type_annotation,
            indent_level + 1,
            is_equal=is_equal
        )
        if not result_:
            print(indent, f'not type_annotation_subtyping({second_function_definition_parameter_type_annotation}, {first_function_definition_parameter_type_annotation})', file=sys.stderr)
            return False, nx.DiGraph()
        else:
            type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
    
    if second_function_definition.vararg_type_annotation != ConcreteClass(module_name='builtins', class_name='NoneType'):
        result_, type_variable_subtyping_digraph_ = type_annotation_subtyping(
            second_function_definition.vararg_type_annotation,
            first_function_definition.vararg_type_annotation,
            indent_level + 1,
            is_equal=is_equal
        )
        if not result_:
            print(indent, f'not type_annotation_subtyping({second_function_definition.vararg_type_annotation}, {first_function_definition.vararg_type_annotation})', file=sys.stderr)
            return False, nx.DiGraph()
        else:
            type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
    
    for (
        second_function_kwonlyargs_name,
        second_function_kwonlyargs_type_annotation
    ) in second_function_definition.kwonlyargs_name_to_type_annotation_dict.items():
        if second_function_kwonlyargs_name not in first_function_definition.kwonlyargs_name_to_type_annotation_dict:
            print(indent, f'{second_function_kwonlyargs_name} not in {first_function_definition.kwonlyargs_name_to_type_annotation_dict.keys()}', file=sys.stderr)
            return False
        else:
            first_function_kwonlyargs_type_annotation = first_function_definition.kwonlyargs_name_to_type_annotation_dict[second_function_kwonlyargs_name]

            result_, type_variable_subtyping_digraph_ = type_annotation_subtyping(
                second_function_kwonlyargs_type_annotation,
                first_function_kwonlyargs_type_annotation,
                indent_level + 1,
                is_equal=is_equal
            )
            if not result_:
                print(indent, f'not type_annotation_subtyping({second_function_kwonlyargs_type_annotation}, {first_function_kwonlyargs_type_annotation})', file=sys.stderr)
                return False, nx.DiGraph()
            else:
                type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
    
    if second_function_definition.kwarg_type_annotation != ConcreteClass(module_name='builtins', class_name='NoneType'):
        result_, type_variable_subtyping_digraph_ = type_annotation_subtyping(
            second_function_definition.kwarg_type_annotation,
            first_function_definition.kwarg_type_annotation,
            indent_level + 1,
            is_equal=is_equal
        )
        if not result_:
            print(indent, f'not type_annotation_subtyping({second_function_definition.kwarg_type_annotation}, {first_function_definition.kwarg_type_annotation})', file=sys.stderr)
            return False, nx.DiGraph()
        else:
            type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
    
    result_, type_variable_subtyping_digraph_ = type_annotation_subtyping(
        first_function_definition.return_value_type_annotation,
        second_function_definition.return_value_type_annotation,
        indent_level + 1,
        is_equal=is_equal
    )
    if not result_:
        print(indent, f'not type_annotation_subtyping({first_function_definition.return_value_type_annotation}, {second_function_definition.return_value_type_annotation})', file=sys.stderr)
        return False, nx.DiGraph()
    else:
        type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
    
    return True, type_variable_subtyping_digraph


def type_of_self_or_cls(concrete_class: ConcreteClass, class_definition: ClassDefinition, indent_level=0):
    indent = '    ' * indent_level
    
    print(indent, f'type_of_self_or_cls {concrete_class}', file=sys.stderr)
    
    if class_definition.type_variable_list:
        return Subscription(concrete_class, tuple(class_definition.type_variable_list))
    else:
        return concrete_class


TYPE_ANNOTATION_SUBTYPING_QUERIES_DICT = dict()

def type_annotation_subtyping(
    first_type_annotation,
    second_type_annotation,
    indent_level=0,
    *,
    is_equal=lambda first_type_annotation, second_type_annotation: first_type_annotation == second_type_annotation
):
    global TYPE_ANNOTATION_SUBTYPING_QUERIES_DICT
    
    if indent_level > 100:
        assert False
    
    indent = '    ' * indent_level

    print(indent, f'type_annotation_subtyping {first_type_annotation} {second_type_annotation}', file=sys.stderr)
    
    if (first_type_annotation, second_type_annotation) in TYPE_ANNOTATION_SUBTYPING_QUERIES_DICT:
        return TYPE_ANNOTATION_SUBTYPING_QUERIES_DICT[(first_type_annotation, second_type_annotation)]
    else:
        # reject recursive lookups of the same parameters
        type_variable_subtyping_digraph = nx.DiGraph()
        
        TYPE_ANNOTATION_SUBTYPING_QUERIES_DICT[(first_type_annotation, second_type_annotation)] = (True, type_variable_subtyping_digraph)

        # handle equalities
        # no modification of `type_variable_subtyping_digraph`
        if is_equal(first_type_annotation, second_type_annotation):
            print(indent, f'is_equal({first_type_annotation}, {second_type_annotation})', file=sys.stderr)
            result = True
        else:
            # handle `TypeVariable`'s
            if isinstance(first_type_annotation, TypeVariable) or isinstance(second_type_annotation, TypeVariable):
                result = True
                type_variable_subtyping_digraph.add_edge(first_type_annotation, second_type_annotation)
            else:
                # handle `Subscription`'s
                if isinstance(first_type_annotation, ConcreteClass) and isinstance(second_type_annotation, Subscription):
                    first_type_concrete_class = first_type_annotation
                    second_type_concrete_class = second_type_annotation.concrete_class

                    first_type_type_annotation_list = []
                    second_type_type_annotation_list = list(second_type_annotation.type_annotation_tuple)

                    first_type_class_definition = look_up_class(first_type_concrete_class, indent_level + 1)
                    second_type_class_definition = look_up_class(second_type_concrete_class, indent_level + 1)

                    instantiated_first_type_class_definition = first_type_class_definition

                    instantiated_second_type_class_definition = instantiate_type_variables_in_class_definition(
                        second_type_class_definition,
                        second_type_type_annotation_list,
                        indent_level + 1
                    )

                    result, type_variable_subtyping_digraph_ = class_definition_subtyping(
                        first_type_annotation,
                        instantiated_first_type_class_definition,
                        second_type_annotation,
                        instantiated_second_type_class_definition,
                        indent_level + 1
                    )
                    
                    type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
                elif isinstance(first_type_annotation, Subscription) and isinstance(second_type_annotation, ConcreteClass):
                    first_type_concrete_class = first_type_annotation.concrete_class
                    second_type_concrete_class = second_type_annotation

                    first_type_type_annotation_list = list(first_type_annotation.type_annotation_tuple)
                    second_type_type_annotation_list = []

                    first_type_class_definition = look_up_class(first_type_concrete_class, indent_level + 1)
                    second_type_class_definition = look_up_class(second_type_concrete_class, indent_level + 1)

                    instantiated_first_type_class_definition = instantiate_type_variables_in_class_definition(
                        first_type_class_definition,
                        first_type_type_annotation_list,
                        indent_level + 1
                    )

                    instantiated_second_type_class_definition = second_type_class_definition

                    result, type_variable_subtyping_digraph_ = class_definition_subtyping(
                        first_type_annotation,
                        instantiated_first_type_class_definition,
                        second_type_annotation,
                        instantiated_second_type_class_definition,
                        indent_level + 1
                    )
                    
                    type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
                elif isinstance(first_type_annotation, Subscription) and isinstance(second_type_annotation, Subscription):
                    first_type_concrete_class = first_type_annotation.concrete_class
                    second_type_concrete_class = second_type_annotation.concrete_class

                    first_type_type_annotation_list = list(first_type_annotation.type_annotation_tuple)
                    second_type_type_annotation_list = list(second_type_annotation.type_annotation_tuple)

                    first_type_class_definition = look_up_class(first_type_concrete_class, indent_level + 1)
                    second_type_class_definition = look_up_class(second_type_concrete_class, indent_level + 1)

                    instantiated_first_type_class_definition = instantiate_type_variables_in_class_definition(
                        first_type_class_definition,
                        first_type_type_annotation_list,
                        indent_level + 1
                    )

                    instantiated_second_type_class_definition = instantiate_type_variables_in_class_definition(
                        second_type_class_definition,
                        second_type_type_annotation_list,
                        indent_level + 1
                    )

                    result, type_variable_subtyping_digraph_ = class_definition_subtyping(
                        first_type_annotation,
                        instantiated_first_type_class_definition,
                        second_type_annotation,
                        instantiated_second_type_class_definition,
                        indent_level + 1
                    )
                    
                    type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
                # handle `ConcreteClass`'s
                # no modification of `type_variable_subtyping_digraph`
                elif isinstance(first_type_annotation, ConcreteClass) and isinstance(second_type_annotation, ConcreteClass):
                    first_type_annotation_runtime_class_or_none = resolve_runtime_class_or_none(first_type_annotation, indent_level + 1)
                    second_type_annotation_runtime_class_or_none = resolve_runtime_class_or_none(second_type_annotation, indent_level + 1)

                    if first_type_annotation_runtime_class_or_none is not None and second_type_annotation_runtime_class_or_none is not None:
                        if second_type_annotation_runtime_class_or_none in first_type_annotation_runtime_class_or_none.__mro__:
                            print(indent, f'{second_type_annotation_runtime_class_or_none} in {first_type_annotation_runtime_class_or_none}.__mro__', file=sys.stderr)
                            result = True
                        else:
                            print(indent, f'{second_type_annotation_runtime_class_or_none} not in {first_type_annotation_runtime_class_or_none}.__mro__', file=sys.stderr)
                            result = False
                    else:
                        first_type_class_definition = look_up_class(first_type_annotation)
                        second_type_class_definition = look_up_class(second_type_annotation)

                        new_first_type_annotation = type_of_self_or_cls(first_type_annotation, first_type_class_definition, indent_level + 1)
                        new_second_type_annotation = type_of_self_or_cls(second_type_annotation, second_type_class_definition, indent_level + 1)

                        if (new_first_type_annotation, new_second_type_annotation) in TYPE_ANNOTATION_SUBTYPING_QUERIES_DICT:
                            result = TYPE_ANNOTATION_SUBTYPING_QUERIES_DICT[(new_first_type_annotation, new_second_type_annotation)]
                        else:
                            result = class_definition_subtyping(
                                new_first_type_annotation,
                                first_type_class_definition,
                                new_second_type_annotation,
                                second_type_class_definition,
                                indent_level + 1
                            )
                # handle `Union`'s
                elif isinstance(first_type_annotation, (Subscription, ConcreteClass)) and isinstance(second_type_annotation, Union):
                    for type_annotation in second_type_annotation:
                        result_, type_variable_subtyping_digraph_ = type_annotation_subtyping(
                            first_type_annotation,
                            type_annotation,
                            indent_level + 1
                        )
                        if result_:
                            type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
                            result = True
                elif isinstance(first_type_annotation, Union) and isinstance(second_type_annotation, Union):
                    result_ = True
                    type_variable_subtyping_digraph_ = nx.DiGraph()
                    for type_annotation in first_type_annotation:
                        result__, type_variable_subtyping_digraph__ = type_annotation_subtyping(
                            type_annotation,
                            second_type_annotation,
                            indent_level + 1
                        )
                        if result__:
                            type_variable_subtyping_digraph_.add_edges_from(type_variable_subtyping_digraph__.edges)
                        else:
                            result_ = False
                            type_variable_subtyping_digraph_ = nx.DiGraph()
                            break
                    
                    result = result_
                    type_variable_subtyping_digraph.add_edges_from(type_variable_subtyping_digraph_.edges)
                            
                else:
                    assert False, (first_type_annotation, second_type_annotation)

        if not result:
            TYPE_ANNOTATION_SUBTYPING_QUERIES_DICT[(first_type_annotation, second_type_annotation)] = (False, type_variable_subtyping_digraph)
        
        return result, type_variable_subtyping_digraph


def find_lowest_subtype_of_type_annotations(type_annotation_list):
    if len(type_annotation_list) == 0:
        subtype = None
    elif len(type_annotation_list) == 1:
        subtype = type_annotation_list[0]
    else:
        subtype = type_annotation_list[0]
        for type_annotation in type_annotation_list[1:]:
            if type_annotation_subtyping(type_annotation, subtype)[0]:
                subtype = type_annotation
    
    return subtype

