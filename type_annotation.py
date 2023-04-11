from enum import Enum
import sys

from attrs import define, frozen


Kind = Enum('Kind', ['CLASS_DEFINITION', 'GLOBAL_FUNCTION_DEFINITION', 'UNION', 'SUBSCRIBED_CLASS', 'TYPE_VARIABLE', 'OBJECT'])


# All type annotations are HASHABLE

class TypeVariable(object):
    pass


@frozen
class ConcreteClass:
    module_name: str
    class_name: str


@frozen
class GlobalFunction:
    module_name: str
    function_name: str


@frozen
class Subscription:
    concrete_class: ConcreteClass
    type_annotation_tuple: tuple


Union = tuple


def type_annotation_from_instance(instance):
    return ConcreteClass(type(instance).__module__, type(instance).__name__)


def iterate_type_variables_in_type_annotation(type_annotation, indent_level=0):
    indent = '    ' * indent_level

    print(indent, f'iterate_type_variables_in_type_annotation {type_annotation}', file=sys.stderr)

    # type_annotation is a ConcreteClass
    if isinstance(type_annotation, ConcreteClass):
        pass
    # type_annotation is a TypeVariable
    elif isinstance(type_annotation, TypeVariable):
        yield type_annotation
    # type_annotation is a Subscription
    elif isinstance(type_annotation, Subscription):
        for child_type_annotation in type_annotation.type_annotation_tuple:
            yield from iterate_type_variables_in_type_annotation(child_type_annotation, indent_level + 1)
    # new
    # type_annotation is a Union
    elif isinstance(type_annotation, Union):
        for child_type_annotation in type_annotation:
            yield from iterate_type_variables_in_type_annotation(child_type_annotation, indent_level + 1)
    else:
        assert False, type_annotation


def replace_type_variables_in_type_annotation(type_annotation, old_type_variable_to_new_type_annotation_dict, indent_level=0):
    indent = '    ' * indent_level

    print(indent, f'replace_type_variables_in_type_annotation {type_annotation}, {old_type_variable_to_new_type_annotation_dict}', file=sys.stderr)

    # type_annotation is a ConcreteClass
    if isinstance(type_annotation, ConcreteClass):
        return type_annotation
    # type_annotation is a TypeVariable
    elif isinstance(type_annotation, TypeVariable):
        if type_annotation in old_type_variable_to_new_type_annotation_dict:
            return old_type_variable_to_new_type_annotation_dict[type_annotation]
        else:
            return type_annotation
    # type_annotation is a Subscription
    elif isinstance(type_annotation, Subscription):
        new_concrete_class= type_annotation.concrete_class
        new_type_annotation_list = [
            replace_type_variables_in_type_annotation(old_type_annotation, old_type_variable_to_new_type_annotation_dict, indent_level + 1)
            for old_type_annotation in type_annotation.type_annotation_tuple
        ]
        return Subscription(new_concrete_class, tuple(new_type_annotation_list))
    # new
    # type_annotation is a Union
    elif isinstance(type_annotation, Union):
        return Union([
            replace_type_variables_in_type_annotation(child_type_annotation, old_type_variable_to_new_type_annotation_dict, indent_level + 1)
            for child_type_annotation in type_annotation
        ])
    else:
        assert False, type_annotation

