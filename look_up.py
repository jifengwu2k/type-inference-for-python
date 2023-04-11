"""
In [1]: from look_up import *

In [2]: from type_annotation import *

In [3]: module_name = 'builtins'

In [4]: import importlib

In [5]: module = importlib.import_module(module_name)

In [6]: global_function_list = [ v for k, v in module.__dict__.items() if callable(v) and not isinstance(v, type) and v.__module__ == module_name]

In [7]: class_list = [ v for k, v in module.__dict__.items() if isinstance(v, type) and v.__module__ == module_name ]

In [8]: for f in global_function_list: look_up_global_function(GlobalFunction(f.__module__, f.__name__))

In [9]: for c in class_list: look_up_class(ConcreteClass(c.__module__, c.__name__))
"""

import ast
import sys

import networkx as nx
from ordered_set import OrderedSet
import typeshed_client.parser

from class_definition import ClassDefinition, instantiate_type_variables_in_class_definition
from function_definition import FunctionDefinition
from type_annotation import *


CLASS_INHERITANCE_GRAPH = nx.DiGraph()

# Parse AST Node to Type Annotation
# Returns an instance of ConcreteClass, TypeVariable, Subscription, list
# new
# a keyword-only parameter for resolving all instances of `Self` and `_typeshed.Self`
def parse_node_to_type_annotation(module_name, node, indent_level=0, *, type_annotation_for_self=None):
    indent = '    ' * indent_level

    print(indent, f'parse_node_to_type_annotation {module_name} {ast.dump(node)}', file=sys.stderr)

    # Name(id='object', ctx=Load())
    # Name(id='_KT', ctx=Load())
    # Create instance of ConcreteClass or TypeVariable
    # new
    # special handling for _typeshed.Self
    if isinstance(node, ast.Name):
        looked_up_name, looked_up_name_kind = look_up_name(module_name, node.id, indent_level + 1)

        # new
        # special handling for _typeshed.Self
        if isinstance(looked_up_name, ConcreteClass) and looked_up_name == ConcreteClass('_typeshed', 'Self'):
            assert type_annotation_for_self is not None
            return type_annotation_for_self
        else:
            assert looked_up_name_kind in (Kind.CLASS_DEFINITION, Kind.UNION, Kind.SUBSCRIBED_CLASS, Kind.TYPE_VARIABLE), (looked_up_name, looked_up_name_kind)
            return looked_up_name

    # "Subscript(value=Name(id='Protocol', ctx=Load()), slice=Index(value=Name(id='_T_co', ctx=Load())), ctx=Load())"
    # Create instance of Subscription
    # new
    # Special handling for typing.Literal, typing_extensions.Literal, typing.ClassVar, typing_extensions.Literal, typing.TypeGuard, typing_extensions.TypeGuard
    # Create instance of ConcreteClass
    elif isinstance(node, ast.Subscript):
        # recursively parse node.value
        # node.value should parse to a ConcreteClass representing a concrete type
        parsed_node_value = parse_node_to_type_annotation(module_name, node.value, indent_level + 1, type_annotation_for_self=type_annotation_for_self)
        assert isinstance(parsed_node_value, ConcreteClass), parsed_node_value

        # recursively parse node.slice.value
        assert isinstance(node.slice, ast.Index), ast.dump(node.slice)
        parsed_node_slice_value = parse_node_to_type_annotation(module_name, node.slice.value, indent_level + 1, type_annotation_for_self=type_annotation_for_self)

        # store the results of parsing node.slice.value in type_annotation_list
        type_annotation_list = list()

        if isinstance(parsed_node_slice_value, Union):
            type_annotation_list.extend(parsed_node_slice_value)
        else:
            type_annotation_list.append(parsed_node_slice_value)

        # new
        # special handling for typing.Literal, typing_extensions.Literal, and typing.ClassVar
        if parsed_node_value in (ConcreteClass('typing', 'Literal'), ConcreteClass('typing_extensions', 'Literal'), ConcreteClass('typing', 'ClassVar')):
            assert all((isinstance(type_annotation, ConcreteClass) for type_annotation in type_annotation_list)), type_annotation_list

            concrete_class_set = set(type_annotation_list)
            assert len(concrete_class_set) == 1, concrete_class_set

            return concrete_class_set.pop()
        # new
        # special handling for typing.TypeGuard and typing_extensions.TypeGuard
        elif parsed_node_value in (ConcreteClass('typing', 'TypeGuard'), ConcreteClass('typing_extensions', 'TypeGuard')):
            return ConcreteClass('builtins', 'bool')
        else:
            return Subscription(concrete_class=parsed_node_value, type_annotation_tuple=tuple(type_annotation_list))
    # new
    # BinOp(left=BinOp(left=BinOp(left=BinOp(left=Name(id='str', ctx=Load()), op=BitOr(), right=Name(id='ReadableBuffer', ctx=Load()))
    # Create instance of Union
    elif isinstance(node, ast.BinOp):
        assert isinstance(node.op, ast.BitOr)

        list_instance = list()

        # recursively parse node.left
        parsed_node_left = parse_node_to_type_annotation(module_name, node.left, indent_level + 1, type_annotation_for_self=type_annotation_for_self)
        
        # update list_instance
        if isinstance(parsed_node_left, Union):
            list_instance.extend(parsed_node_left)
        else:
            list_instance.append(parsed_node_left)
        
        # recursively parse node.right
        parsed_node_right = parse_node_to_type_annotation(module_name, node.right, indent_level + 1, type_annotation_for_self=type_annotation_for_self)

        # update list_instance
        if isinstance(parsed_node_right, Union):
            list_instance.extend(parsed_node_right)
        else:
            list_instance.append(parsed_node_right)

        return Union(list_instance)
    # new
    # Tuple(elts=[Name(id='_KT', ctx=Load()), Name(id='_VT', ctx=Load())], ctx=Load())
    # List(elts=[Name(id='_T', ctx=Load())], ctx=Load())
    elif isinstance(node, (ast.Tuple, ast.List)):
        list_instance = list()

        for elt in node.elts:
            parsed_elt = parse_node_to_type_annotation(module_name, elt, indent_level + 1, type_annotation_for_self=type_annotation_for_self)

            # update list_instance
            if isinstance(parsed_elt, Union):
                list_instance.extend(parsed_elt)
            else:
                list_instance.append(parsed_elt)
        
        return Union(list_instance)
    # new
    # Create instance of ConcreteClass
    elif isinstance(node, ast.Constant):
        # node.value is the literal value
        module_name = type(node.value).__module__
        class_name = type(node.value).__name__

        return ConcreteClass(module_name=module_name, class_name=class_name)
    # new
    # special handling for _typeshed.Self
    elif isinstance(node, ast.Attribute):
        assert isinstance(node.value, ast.Name), ast.dump(node)
        
        looked_up_name, looked_up_name_kind = look_up_name(node.value.id, node.attr, indent_level + 1)
        
        # new
        # special handling for _typeshed.Self
        if isinstance(looked_up_name, ConcreteClass) and looked_up_name == ConcreteClass('_typeshed', 'Self'):
            assert type_annotation_for_self is not None
            return type_annotation_for_self
        else:
            assert looked_up_name_kind in (Kind.CLASS_DEFINITION, Kind.UNION, Kind.SUBSCRIBED_CLASS), (looked_up_name, looked_up_name_kind)
            return looked_up_name
    # new
    # UnaryOp(op=USub(), operand=Constant(value=1, kind=None))
    elif isinstance(node, ast.UnaryOp):
        evaluation_result = ast.literal_eval(node)

        module_name = type(evaluation_result).__module__
        class_name = type(evaluation_result).__name__

        return ConcreteClass(module_name=module_name, class_name=class_name)
    else:
        assert False, ast.dump(node)


# Parse Class
def parse_class(concrete_class: ConcreteClass, class_def: ast.ClassDef, child_nodes: dict, indent_level=0) -> ClassDefinition:
    global CLASS_INHERITANCE_GRAPH
    
    indent = '    ' * indent_level

    print(indent, f'parse_class {concrete_class} {child_nodes.keys()}', file=sys.stderr)

    class_level_type_variable_ordered_set = OrderedSet()

    method_name_to_method_list_dict = dict()

    staticmethod_name_to_staticmethod_list_dict = dict()

    property_name_to_property_type_annotation_dict = dict()

    for base in class_def.bases:
        # Parse AST node to type annotation
        # Returns ConcreteClass, TypeVariable, Subscription, list
        # Should be ConcreteClass or Subscription
        base_type_annotation = parse_node_to_type_annotation(concrete_class.module_name, base, indent_level + 1)

        if isinstance(base_type_annotation, ConcreteClass):
            base_class = base_type_annotation
            base_class_type_annotation_list = []
        elif isinstance(base_type_annotation, Subscription):
            base_class = base_type_annotation.concrete_class
            base_class_type_annotation_list = list(base_type_annotation.type_annotation_tuple)
        else:
            assert False, base_type_annotation
            
        CLASS_INHERITANCE_GRAPH.add_node(concrete_class)
        CLASS_INHERITANCE_GRAPH.add_edge(concrete_class, base_class)
        
        # Update class_level_type_variable_ordered_set
        for base_class_type_annotation in base_class_type_annotation_list:
            class_level_type_variable_ordered_set.update(iterate_type_variables_in_type_annotation(base_class_type_annotation, indent_level + 1))
        
        # Eagerly resolve base class
        print(indent, f'looking up base class {base_class}', file=sys.stderr)
        base_class_definition = look_up_class(base_class, indent_level + 1)

        print(indent, f'instantiating type variables in base class {base_class} with {base_class_type_annotation_list}', file=sys.stderr)
        base_class_definition_with_instantiated_type_variables = instantiate_type_variables_in_class_definition(base_class_definition, base_class_type_annotation_list, indent_level + 1)

        print(indent, f'adding all methods to method_name_to_method_list_dict', file=sys.stderr)
        method_name_to_method_list_dict.update(base_class_definition_with_instantiated_type_variables.method_name_to_method_list_dict)

        print(indent, f'adding all staticmethods to staticmethod_name_to_staticmethod_list_dict', file=sys.stderr)
        staticmethod_name_to_staticmethod_list_dict.update(base_class_definition_with_instantiated_type_variables.staticmethod_name_to_staticmethod_list_dict)

        print(indent, f'adding all properties to property_name_to_property_type_annotation_dict', file=sys.stderr)
        property_name_to_property_type_annotation_dict.update(base_class_definition_with_instantiated_type_variables.property_name_to_property_type_annotation_dict)


    class_level_type_variable_list = list(class_level_type_variable_ordered_set)
    
    if class_level_type_variable_list:
        type_of_self_or_cls = Subscription(concrete_class, tuple(class_level_type_variable_list))
    else:
        type_of_self_or_cls = concrete_class
    
    # Replacing the type of the first parameter of all methods in method_name_to_method_list_dict to type_of_self_or_cls
    for method_name, method_list in method_name_to_method_list_dict.items():
        for method in method_list:
            parameter_type_annotation_list = method.parameter_type_annotation_list
            parameter_type_annotation_list[0] = type_of_self_or_cls

    # Add methods and properties
    for child_node_name, child_node in child_nodes.items():
        # "FunctionDef(name='__iter__', args=arguments(posonlyargs=[], args=[arg(arg='self', annotation=None, type_comment=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]), body=[Expr(value=Constant(value=Ellipsis, kind=None))], decorator_list=[Name(id='abstractmethod', ctx=Load())], returns=Subscript(value=Name(id='Iterator', ctx=Load()), slice=Index(value=Name(id='_T_co', ctx=Load())), ctx=Load()), type_comment=None)"
        child_node_ast = child_node.ast
        
        if isinstance(child_node_ast, ast.FunctionDef):
            # Is Method (including `classmethod`'s, not including `staticmethod`'s)
            if is_method(child_node_ast):
                method_name_to_method_list_dict[child_node_name] = [
                    parse_method(concrete_class, child_node_ast, type_of_self_or_cls, class_level_type_variable_ordered_set, indent_level + 1) 
                ]
            else:
                staticmethod_name_to_staticmethod_list_dict[child_node_name] = [
                    parse_global_function_or_staticmethod(concrete_class, child_node_ast, indent_level + 1)
                ]
        elif isinstance(child_node_ast, typeshed_client.parser.OverloadedName):
            # Is Method (including `classmethod`'s, not including `staticmethod`'s)
            if all((is_method(definition) for definition in child_node_ast.definitions)):
                method_name_to_method_list_dict[child_node_name] = [ 
                    parse_method(concrete_class, definition, type_of_self_or_cls, class_level_type_variable_ordered_set, indent_level + 1)
                    for definition in child_node_ast.definitions
                ]
            else:
                assert all((not is_method(definition) for definition in child_node_ast.definitions))
                staticmethod_name_to_staticmethod_list_dict[child_node_name] = [ 
                    parse_global_function_or_staticmethod(concrete_class, definition, indent_level + 1)
                    for definition in child_node_ast.definitions
                ]
        elif isinstance(child_node_ast, ast.AnnAssign):
            property_name_to_property_type_annotation_dict[child_node_name] = parse_node_to_type_annotation(
                concrete_class.module_name,
                child_node_ast.annotation,
                indent_level + 1
            )
        else:
            assert False, child_node_ast
    
    return ClassDefinition(
        class_level_type_variable_list,
        method_name_to_method_list_dict,
        staticmethod_name_to_staticmethod_list_dict,
        property_name_to_property_type_annotation_dict
    )


# Is Method (including `classmethod`'s, not including `staticmethod`'s)
def is_method(function_def):
    args = function_def.args
    args_args = args.args
    return args_args[0].arg in ('self', 'cls', 'metacls')


# Parse Method (including `classmethod`'s, not including `staticmethod`'s)
# def __new__(cls: type[Self], __iterable: Iterable[_T_co]) -> Self: ...
# "FunctionDef(name='__new__', args=arguments(posonlyargs=[], args=[arg(arg='cls', annotation=Subscript(value=Name(id='type', ctx=Load()), slice=Index(value=Name(id='Self', ctx=Load())), ctx=Load()), type_comment=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]), body=[Expr(value=Constant(value=Ellipsis, kind=None))], decorator_list=[Name(id='overload', ctx=Load())], returns=Name(id='Self', ctx=Load()), type_comment=None)"
# def __contains__(self, __o: object) -> bool: ...
# "FunctionDef(name='__contains__', args=arguments(posonlyargs=[], args=[arg(arg='self', annotation=None, type_comment=None), arg(arg='__o', annotation=Name(id='object', ctx=Load()), type_comment=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]), body=[Expr(value=Constant(value=Ellipsis, kind=None))], decorator_list=[], returns=Name(id='bool', ctx=Load()), type_comment=None)"
def parse_method(concrete_class, function_def, type_of_self_or_cls, class_level_type_variable_set, indent_level=0):
    indent = '    ' * indent_level

    print(indent, f'parse_method {concrete_class} {function_def.name}', file=sys.stderr)

    # copy the original class_level_type_variable_set
    class_level_type_variable_set_copy = class_level_type_variable_set.copy()

    parameter_type_annotation_list = list()

    args = function_def.args

    args_posonlyargs = args.posonlyargs
    assert not args_posonlyargs

    args_args = args.args

    # the first parameter of a method should be 'self' or 'cls' or 'metacls'
    assert args_args[0].arg in ('self', 'cls', 'metacls'), args_args[0].arg
    parameter_type_annotation_list.append(type_of_self_or_cls)

    for i, arg in enumerate(args_args[1:]):
        # "arg(arg='__iterable', annotation=Subscript(value=Name(id='SupportsIter', ctx=Load()), slice=Index(value=Name(id='_SupportsNextT', ctx=Load())), ctx=Load()), type_comment=None)"
        # "arg(arg='__o', annotation=Name(id='object', ctx=Load()), type_comment=None)"
        arg_type_annotation = parse_node_to_type_annotation(concrete_class.module_name, arg.annotation, indent_level + 1, type_annotation_for_self=type_of_self_or_cls)

        class_level_type_variable_set_copy.update(iterate_type_variables_in_type_annotation(arg_type_annotation, indent_level + 1))

        parameter_type_annotation_list.append(arg_type_annotation)
    
    args_vararg = args.vararg
    if args_vararg:
        vararg_type_annotation = parse_node_to_type_annotation(concrete_class.module_name, args_vararg.annotation, indent_level + 1, type_annotation_for_self=type_of_self_or_cls)
    
        class_level_type_variable_set_copy.update(iterate_type_variables_in_type_annotation(vararg_type_annotation, indent_level + 1))
    else:
        vararg_type_annotation = type_annotation_from_instance(None)

    kwonlyargs_name_to_type_annotation_dict = dict()

    args_kwonlyargs = args.kwonlyargs
    for kwonlyarg in args_kwonlyargs:
        kwonlyarg_type_annotation = parse_node_to_type_annotation(concrete_class.module_name, kwonlyarg.annotation, indent_level + 1, type_annotation_for_self=type_of_self_or_cls)
        
        kwonlyargs_name_to_type_annotation_dict[kwonlyarg.arg] = kwonlyarg_type_annotation

        class_level_type_variable_set_copy.update(iterate_type_variables_in_type_annotation(kwonlyarg_type_annotation, indent_level + 1))

    args_kwarg = args.kwarg
    if args_kwarg:
        kwarg_type_annotation = parse_node_to_type_annotation(concrete_class.module_name, args_kwarg.annotation, indent_level + 1, type_annotation_for_self=type_of_self_or_cls)

        class_level_type_variable_set_copy.update(iterate_type_variables_in_type_annotation(kwarg_type_annotation, indent_level + 1))
    else:
        kwarg_type_annotation = type_annotation_from_instance(None)

    return_value_type_annotation = parse_node_to_type_annotation(concrete_class.module_name, function_def.returns, indent_level + 1, type_annotation_for_self=type_of_self_or_cls)
    
    class_level_type_variable_set_copy.update(iterate_type_variables_in_type_annotation(return_value_type_annotation, indent_level + 1))

    method_level_type_variable_set = class_level_type_variable_set_copy - class_level_type_variable_set

    return FunctionDefinition(
        type_variable_list=list(method_level_type_variable_set),
        parameter_type_annotation_list=parameter_type_annotation_list,
        vararg_type_annotation=vararg_type_annotation,
        kwonlyargs_name_to_type_annotation_dict=kwonlyargs_name_to_type_annotation_dict,
        kwarg_type_annotation=kwarg_type_annotation,
        return_value_type_annotation=return_value_type_annotation
    )


# Parse Global Function or staticmethod
# def all(__iterable: Iterable[object]) -> bool: ...
# "FunctionDef(name='all', args=arguments(posonlyargs=[], args=[arg(arg='__iterable', annotation=Subscript(value=Name(id='Iterable', ctx=Load()), slice=Index(value=Name(id='object', ctx=Load())), ctx=Load()), type_comment=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]), body=[Expr(value=Constant(value=Ellipsis, kind=None))], decorator_list=[], returns=Name(id='bool', ctx=Load()), type_comment=None)"
# def breakpoint(*args: Any, **kws: Any) -> None: ...
# "FunctionDef(name='breakpoint', args=arguments(posonlyargs=[], args=[], vararg=arg(arg='args', annotation=Name(id='Any', ctx=Load()), type_comment=None), kwonlyargs=[], kw_defaults=[], kwarg=arg(arg='kws', annotation=Name(id='Any', ctx=Load()), type_comment=None), defaults=[]), body=[Expr(value=Constant(value=Ellipsis, kind=None))], decorator_list=[], returns=Constant(value=None, kind=None), type_comment=None)"
def parse_global_function_or_staticmethod(global_function_or_concrete_class, function_def: ast.FunctionDef, indent_level=0) -> FunctionDefinition:
    indent = '    ' * indent_level

    print(indent, f'parse_global_function_or_staticmethod {global_function_or_concrete_class}', file=sys.stderr)

    global_function_level_type_variable_ordered_set = OrderedSet()

    parameter_type_annotation_list = list()

    args = function_def.args

    args_posonlyargs = args.posonlyargs
    assert not args_posonlyargs

    args_args = args.args

    for i, arg in enumerate(args_args):
        # "arg(arg='__iterable', annotation=Subscript(value=Name(id='SupportsIter', ctx=Load()), slice=Index(value=Name(id='_SupportsNextT', ctx=Load())), ctx=Load()), type_comment=None)"
        # "arg(arg='__o', annotation=Name(id='object', ctx=Load()), type_comment=None)"
        arg_type_annotation = parse_node_to_type_annotation(global_function_or_concrete_class.module_name, arg.annotation, indent_level + 1)

        global_function_level_type_variable_ordered_set.update(iterate_type_variables_in_type_annotation(arg_type_annotation, indent_level + 1))

        parameter_type_annotation_list.append(arg_type_annotation)
    
    args_vararg = args.vararg
    if args_vararg:
        vararg_type_annotation = parse_node_to_type_annotation(global_function_or_concrete_class.module_name, args_vararg.annotation, indent_level + 1)
    
        global_function_level_type_variable_ordered_set.update(iterate_type_variables_in_type_annotation(vararg_type_annotation, indent_level + 1))
    else:
        vararg_type_annotation = type_annotation_from_instance(None)

    kwonlyargs_name_to_type_annotation_dict = dict()

    args_kwonlyargs = args.kwonlyargs
    for kwonlyarg in args_kwonlyargs:
        kwonlyarg_type_annotation = parse_node_to_type_annotation(global_function_or_concrete_class.module_name, kwonlyarg.annotation, indent_level + 1)
        
        kwonlyargs_name_to_type_annotation_dict[kwonlyarg.arg] = kwonlyarg_type_annotation

        global_function_level_type_variable_ordered_set.update(iterate_type_variables_in_type_annotation(kwonlyarg_type_annotation, indent_level + 1))

    args_kwarg = args.kwarg
    if args_kwarg:
        kwarg_type_annotation = parse_node_to_type_annotation(global_function_or_concrete_class.module_name, args_kwarg.annotation, indent_level + 1)

        global_function_level_type_variable_ordered_set.update(iterate_type_variables_in_type_annotation(kwarg_type_annotation, indent_level + 1))
    else:
        kwarg_type_annotation = type_annotation_from_instance(None)

    return_value_type_annotation = parse_node_to_type_annotation(global_function_or_concrete_class.module_name, function_def.returns, indent_level + 1)
    
    global_function_level_type_variable_ordered_set.update(iterate_type_variables_in_type_annotation(return_value_type_annotation, indent_level + 1))

    return FunctionDefinition(
        type_variable_list=list(global_function_level_type_variable_ordered_set),
        parameter_type_annotation_list=parameter_type_annotation_list,
        vararg_type_annotation=vararg_type_annotation,
        kwonlyargs_name_to_type_annotation_dict=kwonlyargs_name_to_type_annotation_dict,
        kwarg_type_annotation=kwarg_type_annotation,
        return_value_type_annotation=return_value_type_annotation
    )


# Look Up Name

# Cache with predefined special cases
module_name_name_tuple_to_kind_type_annotation_tuple_dict = {
    ('typing_extensions', 'Literal'): (ConcreteClass('typing_extensions', 'Literal'), Kind.CLASS_DEFINITION),
    ('typing_extensions', 'LiteralString'): (ConcreteClass('builtins', 'str'), Kind.CLASS_DEFINITION),
    ('typing_extensions', 'TypeGuard'): (ConcreteClass('typing_extensions', 'TypeGuard'), Kind.CLASS_DEFINITION),
    ('typing', 'Any'): (ConcreteClass('typing', 'Any'), Kind.CLASS_DEFINITION),
    ('typing', 'Generic'): (ConcreteClass('typing', 'Generic'), Kind.CLASS_DEFINITION),
    ('typing', 'ClassVar'): (ConcreteClass('typing', 'ClassVar'), Kind.CLASS_DEFINITION),
    ('typing', 'Literal'): (ConcreteClass('typing', 'Literal'), Kind.CLASS_DEFINITION),
    ('typing', 'LiteralString'): (ConcreteClass('builtins', 'str'), Kind.CLASS_DEFINITION),
    ('typing', 'Protocol'): (ConcreteClass('typing', 'Protocol'), Kind.CLASS_DEFINITION),
    ('typing', 'TypeGuard'): (ConcreteClass('typing', 'TypeGuard'), Kind.CLASS_DEFINITION),
    ('_typeshed', 'Self'): (ConcreteClass('_typeshed', 'Self'), Kind.CLASS_DEFINITION)
}

def look_up_name(module_name: str, name: str, indent_level=0):
    global module_name_name_tuple_to_kind_type_annotation_tuple_dict
    
    indent = '    ' * indent_level

    print(indent, f'look_up_name {module_name} {name} {look_up_name}', file=sys.stderr)
    
    if (module_name, name) in module_name_name_tuple_to_kind_type_annotation_tuple_dict:
        print(indent, 'cache hit', file=sys.stderr)
        return module_name_name_tuple_to_kind_type_annotation_tuple_dict[(module_name, name)]
    else:
        print(indent, 'cache miss', file=sys.stderr)

        # Initialize to (TypeVariable(), Kind.TYPE_VARIABLE) to handle potential recursive lookups
        type_variable_for_module_name_name_tuple = TypeVariable()
        module_name_name_tuple_to_kind_type_annotation_tuple_dict[(module_name, name)] = (type_variable_for_module_name_name_tuple, Kind.TYPE_VARIABLE)

        module_stub_names_dict = typeshed_client.parser.get_stub_names(module_name)
        
        if name in module_stub_names_dict:
            name_info = module_stub_names_dict[name]
            name_info_ast = name_info.ast

            # It is a concrete class
            if isinstance(name_info_ast, ast.ClassDef):
                return_value = (ConcreteClass(module_name, name), Kind.CLASS_DEFINITION)
            # It is a global function
            elif isinstance(name_info_ast, ast.FunctionDef):
                return_value = (GlobalFunction(module_name, name), Kind.GLOBAL_FUNCTION_DEFINITION)
            elif isinstance(name_info_ast, typeshed_client.parser.OverloadedName):
                assert all((isinstance(definition, ast.FunctionDef) for definition in name_info_ast.definitions))
                return_value = (GlobalFunction(module_name, name), Kind.GLOBAL_FUNCTION_DEFINITION)
            # It is an imported name
            elif isinstance(name_info_ast, typeshed_client.parser.ImportedName):
                new_module_name = '.'.join(name_info_ast.module_name)
                new_name = name_info_ast.name

                return_value = look_up_name(new_module_name, new_name, indent_level + 1)
            # _T = TypeVar("_T")
            # _T_co = TypeVar("_T_co", covariant=True)
            # _OpenFile = StrOrBytesPath | int  # noqa: Y026  # TODO: Use TypeAlias once mypy bugs are fixed
            # _LiteralInteger = _PositiveInteger | _NegativeInteger | Literal[0]
            # EnvironmentError = OSError
            # CLASS_DEFINITION, UNION, SUBSCRIBED_CLASS, TYPE_VARIABLE, OBJECT
            elif isinstance(name_info_ast, ast.Assign):
                name_info_ast_value = name_info_ast.value

                # If the RHS is an `ast.Call` and the called function is 'TypeVar'
                # We conclude that we have encountered a type variable
                if isinstance(name_info_ast_value, ast.Call) and name_info_ast_value.func.id == 'TypeVar':
                    return_value = (TypeVariable(), Kind.TYPE_VARIABLE)
                # Otherwise, we call `parse_node_to_type_annotation` to handle that.
                else:
                    parsed_name_info_ast_value = parse_node_to_type_annotation(
                        module_name,
                        name_info_ast_value,
                        indent_level + 1
                    )

                    if isinstance(parsed_name_info_ast_value, ConcreteClass):
                        return_value = (parsed_name_info_ast_value, Kind.CLASS_DEFINITION)
                    elif isinstance(parsed_name_info_ast_value, Union):
                        return_value = (parsed_name_info_ast_value, Kind.UNION)
                    elif isinstance(parsed_name_info_ast_value, Subscription):
                        return_value = (parsed_name_info_ast_value, Kind.SUBSCRIBED_CLASS)
                    else:
                        assert False, parsed_name_info_ast_value
            
            # _PositiveInteger: TypeAlias = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
            # ReadOnlyBuffer: TypeAlias = bytes  # stable
            # WriteableBuffer: TypeAlias = bytearray | memoryview | array.array[Any] | mmap.mmap | ctypes._CData
            # _ClassInfo: TypeAlias = type | types.UnionType | tuple[_ClassInfo, ...]
            # NotImplemented: _NotImplementedType
            # Ellipsis: ellipsis
            elif isinstance(name_info_ast, ast.AnnAssign):
                name_info_ast_value = name_info_ast.value

                # If the RHS is not None, we call `parse_node_to_type_annotation` to handle that.
                if name_info_ast_value is not None:
                    parsed_name_info_ast_value = parse_node_to_type_annotation(
                        module_name,
                        name_info_ast_value,
                        indent_level + 1
                    )

                    if isinstance(parsed_name_info_ast_value, ConcreteClass):
                        return_value = (parsed_name_info_ast_value, Kind.CLASS_DEFINITION)
                    elif isinstance(parsed_name_info_ast_value, Union):
                        return_value = (parsed_name_info_ast_value, Kind.UNION)
                    elif isinstance(parsed_name_info_ast_value, Subscription):
                        return_value = (parsed_name_info_ast_value, Kind.SUBSCRIBED_CLASS)
                    else:
                        assert False, parsed_name_info_ast_value
                # If the RHS is None, we call `parse_node_to_type_annotation` on the annotation of the LHS.
                else:
                    name_info_ast_annotation = name_info_ast.annotation

                    parsed_name_info_ast_annotation = parse_node_to_type_annotation(
                        module_name,
                        name_info_ast_annotation,
                        indent_level + 1
                    )

                    return_value = (parsed_name_info_ast_annotation, Kind.OBJECT)
            else:
                assert False, name_info_ast
        # look up class_name in builtins as a backup plan
        else:
            assert module_name != 'builtins'

            return_value =  look_up_name('builtins', name, indent_level + 1)

        module_name_name_tuple_to_kind_type_annotation_tuple_dict[(module_name, name)] = return_value
        return return_value


# Look Up Class

# Cache
concrete_class_to_class_definition_dict = {
    ConcreteClass('builtins', 'NoneType'): ClassDefinition(
        type_variable_list=[],
        method_name_to_method_list_dict={
            '__bool__': [
                FunctionDefinition(
                    type_variable_list=[],
                    parameter_type_annotation_list=[ConcreteClass('builtins', 'NoneType')],
                    vararg_type_annotation=ConcreteClass('builtins', 'NoneType'),
                    kwonlyargs_name_to_type_annotation_dict=dict(),
                    kwarg_type_annotation=ConcreteClass('builtins', 'NoneType'),
                    return_value_type_annotation=ConcreteClass('builtins', 'bool')
                )
            ]
        },
        staticmethod_name_to_staticmethod_list_dict=dict(),
        property_name_to_property_type_annotation_dict=dict()
   ),
}

def look_up_class(concrete_class: ConcreteClass, indent_level=0) -> ClassDefinition:
    global concrete_class_to_class_definition_dict
    
    indent = '    ' * indent_level

    print(indent, f'look_up_class {concrete_class}', file=sys.stderr)
    
    if concrete_class in concrete_class_to_class_definition_dict:
        print(indent, 'cache hit', file=sys.stderr)
        return concrete_class_to_class_definition_dict[concrete_class]
    else:
        print(indent, 'cache miss', file=sys.stderr)

        module_stub_names_dict = typeshed_client.parser.get_stub_names(concrete_class.module_name)
        name_info = module_stub_names_dict[concrete_class.class_name]
        
        if isinstance(name_info.ast, ast.ClassDef):
            return_value = parse_class(concrete_class, name_info.ast, name_info.child_nodes, indent_level + 1)
        else:
            return_value = ClassDefinition(
                type_variable_list=list(),
                method_name_to_method_list_dict=dict(),
                staticmethod_name_to_staticmethod_list_dict=dict(),
                property_name_to_property_type_annotation_dict=dict()
            )

        concrete_class_to_class_definition_dict[concrete_class] = return_value
        return return_value


# Look Up Global Function

# Cache
global_function_to_function_definition_dict = dict()

def look_up_global_function(global_function: GlobalFunction, indent_level=0) -> FunctionDefinition:
    global global_function_to_function_definition_dict
    
    indent = '    ' * indent_level

    print(indent, f'look_up_global_function {global_function}', file=sys.stderr)
    
    if global_function in global_function_to_function_definition_dict:
        print(indent, 'cache hit', file=sys.stderr)
        return global_function_to_function_definition_dict[global_function]
    else:
        print(indent, 'cache miss', file=sys.stderr)

        module_stub_names_dict = typeshed_client.parser.get_stub_names(global_function.module_name)
        name_info = module_stub_names_dict[global_function.function_name]
        
        if isinstance(name_info.ast, ast.FunctionDef):
            return_value = [ parse_global_function_or_staticmethod(global_function, name_info.ast, indent_level + 1) ]
        elif isinstance(name_info.ast, typeshed_client.parser.OverloadedName):
            return_value = [
                parse_global_function_or_staticmethod(global_function, definition, indent_level + 1)
                for definition in name_info.ast.definitions
            ]

        global_function_to_function_definition_dict[global_function] = return_value
        return return_value
