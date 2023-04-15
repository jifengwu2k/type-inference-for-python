import sys

from disjoint_set import DisjointSet
from more_itertools import pairwise

from subtyping import find_lowest_subtype_of_type_annotations_or_none
from type_annotation import *


def simplify_type_variables(indent_level=0):
    global type_handle_to_concrete_typing_constraints_dict, type_variable_to_type_handle_set_dict

    indent = '    ' * indent_level
    print(indent, 'simplify_type_variables', file=sys.stderr)

    # Split into disjoint sets
    disjoint_sets = DisjointSet()

    for type_variable, type_handle_set in type_variable_to_type_handle_set_dict.items():
        if len(type_handle_set) > 1:
            for first, second in pairwise(type_handle_set):
                disjoint_sets.union(first, second)
        else:
            disjoint_sets.find(next(iter(type_handle_set)))

    # Associate each disjoint set with a new `TypeVariable`
    disjoint_set_index_to_new_type_variable_dict = dict()
    old_type_variable_to_new_type_variable_dict = dict()
    new_type_variable_to_type_handle_set_dict = dict()

    for type_variable, type_handle_set in type_variable_to_type_handle_set_dict.items():
        for i, disjoint_set in enumerate(
                disjoint_sets.itersets()
        ):
            if type_handle_set.issubset(disjoint_set):
                if i not in disjoint_set_index_to_new_type_variable_dict:
                    new_type_variable = TypeVariable()
                    disjoint_set_index_to_new_type_variable_dict[i] = new_type_variable
                    new_type_variable_to_type_handle_set_dict[new_type_variable] = disjoint_set
                old_type_variable_to_new_type_variable_dict[type_variable] = disjoint_set_index_to_new_type_variable_dict[i]

    print(indent, 'old_type_variable_to_new_type_variable_dict', old_type_variable_to_new_type_variable_dict, file=sys.stderr)

    # Replace each old `TypeVariable` with the corresponding new `TypeVariable`
    # Modifies `type_handle_to_concrete_typing_constraints_dict`, `type_variable_to_type_handle_set_dict`
    for type_handle in type_handle_to_concrete_typing_constraints_dict:
        implementation = type_handle_to_concrete_typing_constraints_dict[type_handle]
        if is_type_annotation(implementation):
            new_implementation = replace_type_variables_in_type_annotation(
                implementation,
                old_type_variable_to_new_type_variable_dict,
                indent_level + 1
            )
            type_handle_to_concrete_typing_constraints_dict[type_handle] = new_implementation

    type_variable_to_type_handle_set_dict = new_type_variable_to_type_handle_set_dict

    # For each disjoint set, if it contains `TypeHandle`'s whose concrete typing constraints are type annotations,
    # We calculate the lowest subtype of these type annotations and set every `TypeHandle` within the disjoint set to the lowest subtype.
    lowest_subtype_of_type_annotations_or_none_list = []
    type_handle_to_resolve_set_list = []

    for type_variable, type_handle_set in type_variable_to_type_handle_set_dict.items():
        type_annotation_list = []
        type_handle_to_resolve_set = set()

        for type_handle in type_handle_set:
            implementation = type_handle_to_concrete_typing_constraints_dict[type_handle]
            if isinstance(implementation, (ConcreteClass, Subscription)):
                type_annotation_list.append(implementation)
            elif isinstance(implementation, (TypeInferenceClass, TypeInferenceUnknown)):
                type_handle_to_resolve_set.add(type_handle)
            else:
                assert False, f'unknown '

        lowest_subtype_of_type_annotations_or_none = find_lowest_subtype_of_type_annotations_or_none(type_annotation_list)

        lowest_subtype_of_type_annotations_or_none_list.append(lowest_subtype_of_type_annotations_or_none)
        type_handle_to_resolve_set_list.append(type_handle_to_resolve_set)

    type_variable_to_type_annotation_dict = dict()

    for i, type_variable, in enumerate(type_variable_to_type_handle_set_dict):
        lowest_subtype_of_type_annotations_or_none = lowest_subtype_of_type_annotations_or_none_list[i]
        type_handle_to_resolve_set = type_handle_to_resolve_set_list[i]
        if lowest_subtype_of_type_annotations_or_none is not None:
            type_variable_to_type_annotation_dict[type_variable] = lowest_subtype_of_type_annotations_or_none
        else:
            assert type_handle_to_resolve_set, 'if lowest_subtype_of_type_annotations_or_none is None, type_handle_to_resolve_set should not be empty'

    for type_variable, type_annotation in type_variable_to_type_annotation_dict.items():
        if type_handle in type_variable_to_type_handle_set_dict:
            for type_handle in type_variable_to_type_handle_set_dict[type_variable]:
                set_to_type_annotation(type_handle, type_annotation)

    for type_variable in type_variable_to_type_annotation_dict:
        type_variable_to_type_handle_set_dict.pop(type_variable, None)

    for type_handle_ in type_handle_to_concrete_typing_constraints_dict:
        implementation_ = type_handle_to_concrete_typing_constraints_dict[type_handle_]
        if isinstance(implementation_, (TypeVariable, ConcreteClass, Subscription)):
            new_implementation_ = replace_type_variables_in_type_annotation(implementation_,
                                                                            type_variable_to_type_annotation_dict)
            type_handle_to_concrete_typing_constraints_dict[type_handle_] = new_implementation_