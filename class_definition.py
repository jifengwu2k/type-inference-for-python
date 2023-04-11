import sys

from attrs import define

from function_definition import FunctionDefinition
from type_annotation import *


@define
class ClassDefinition:
    type_variable_list: list
    # changed from method_name_to_method_dict
    method_name_to_method_list_dict: dict
    # new
    # support staticmethod
    staticmethod_name_to_staticmethod_list_dict: dict
    # new
    # support properties
    property_name_to_property_type_annotation_dict: dict


def instantiate_type_variables_in_class_definition(class_definition: ClassDefinition, type_annotation_list: list, indent_level=0) -> ClassDefinition:
    indent = '    ' * indent_level

    print(indent, f'instantiate_type_variables_in_class_definition {class_definition} {type_annotation_list}', file=sys.stderr)

    assert len(type_annotation_list) >= len(class_definition.type_variable_list)

    old_type_variable_to_new_type_annotation_dict = {
        old_type_variable: new_type_annotation
        for old_type_variable, new_type_annotation in zip(class_definition.type_variable_list, type_annotation_list)
    }
    
    new_type_variable_list = [
        new_type_annotation
        for new_type_annotation in old_type_variable_to_new_type_annotation_dict.values()
        if isinstance(new_type_annotation, TypeVariable)
    ]

    # new_method_name_to_method_list_dict
    new_method_name_to_method_list_dict = dict()
    
    for method_name, method_list in class_definition.method_name_to_method_list_dict.items():
        new_method_name = method_name
        new_method_list = list()

        for method in method_list:
            # Create method_level_old_type_variable_to_new_type_annotation_dict
            method_level_old_type_variable_to_new_type_annotation_dict = old_type_variable_to_new_type_annotation_dict.copy()
            for method_level_type_variable in method.type_variable_list:
                method_level_old_type_variable_to_new_type_annotation_dict[method_level_type_variable] = method_level_type_variable

            new_method_type_variable_list = method.type_variable_list

            new_method_parameter_type_annotation_list = [
                replace_type_variables_in_type_annotation(old_parameter_type_annotation, method_level_old_type_variable_to_new_type_annotation_dict, indent_level + 1)
                for old_parameter_type_annotation in method.parameter_type_annotation_list
            ]

            new_method_vararg_type_annotation = replace_type_variables_in_type_annotation(
                method.vararg_type_annotation,
                method_level_old_type_variable_to_new_type_annotation_dict,
                indent_level + 1
            )

            new_method_kwonlyargs_name_to_type_annotation_dict = {
                kwonlyargs_name: replace_type_variables_in_type_annotation(old_kwonlyargs_type_annotation, method_level_old_type_variable_to_new_type_annotation_dict, indent_level + 1)
                for kwonlyargs_name, old_kwonlyargs_type_annotation in method.kwonlyargs_name_to_type_annotation_dict.items()
            }

            new_method_kwarg_type_annotation = replace_type_variables_in_type_annotation(
                method.kwarg_type_annotation,
                method_level_old_type_variable_to_new_type_annotation_dict,
                indent_level + 1
            )

            new_method_return_value_type_annotation = replace_type_variables_in_type_annotation(method.return_value_type_annotation, method_level_old_type_variable_to_new_type_annotation_dict, indent_level + 1)

            new_method = FunctionDefinition(new_method_type_variable_list, new_method_parameter_type_annotation_list, new_method_vararg_type_annotation, new_method_kwonlyargs_name_to_type_annotation_dict, new_method_kwarg_type_annotation, new_method_return_value_type_annotation)

            new_method_list.append(new_method)

        new_method_name_to_method_list_dict[method_name] = new_method_list

    # new_staticmethod_name_to_staticmethod_list_dict
    new_staticmethod_name_to_staticmethod_list_dict = dict()
    
    for staticmethod_name, staticmethod_list in class_definition.staticmethod_name_to_staticmethod_list_dict.items():
        new_staticmethod_name = staticmethod_name
        new_staticmethod_list = list()

        for staticmethod in staticmethod_list:
            # Create staticmethod_level_old_type_variable_to_new_type_annotation_dict
            staticmethod_level_old_type_variable_to_new_type_annotation_dict = dict()
            for staticmethod_level_type_variable in staticmethod.type_variable_list:
                staticmethod_level_old_type_variable_to_new_type_annotation_dict[staticmethod_level_type_variable] = staticmethod_level_type_variable

            new_staticmethod_type_variable_list = staticmethod.type_variable_list

            new_staticmethod_parameter_type_annotation_list = [
                replace_type_variables_in_type_annotation(old_parameter_type_annotation, staticmethod_level_old_type_variable_to_new_type_annotation_dict, indent_level + 1)
                for old_parameter_type_annotation in staticmethod.parameter_type_annotation_list
            ]

            new_staticmethod_vararg_type_annotation = replace_type_variables_in_type_annotation(
                staticmethod.vararg_type_annotation,
                staticmethod_level_old_type_variable_to_new_type_annotation_dict,
                indent_level + 1
            )

            new_staticmethod_kwonlyargs_name_to_type_annotation_dict = {
                kwonlyargs_name: replace_type_variables_in_type_annotation(old_kwonlyargs_type_annotation, staticmethod_level_old_type_variable_to_new_type_annotation_dict, indent_level + 1)
                for kwonlyargs_name, old_kwonlyargs_type_annotation in staticmethod.kwonlyargs_name_to_type_annotation_dict.items()
            }

            new_staticmethod_kwarg_type_annotation = replace_type_variables_in_type_annotation(
                staticmethod.kwarg_type_annotation,
                staticmethod_level_old_type_variable_to_new_type_annotation_dict,
                indent_level + 1
            )

            new_staticmethod_return_value_type_annotation = replace_type_variables_in_type_annotation(staticmethod.return_value_type_annotation, staticmethod_level_old_type_variable_to_new_type_annotation_dict, indent_level + 1)

            new_staticmethod = FunctionDefinition(new_staticmethod_type_variable_list, new_staticmethod_parameter_type_annotation_list, new_staticmethod_vararg_type_annotation, new_staticmethod_kwonlyargs_name_to_type_annotation_dict, new_staticmethod_kwarg_type_annotation, new_staticmethod_return_value_type_annotation)

            new_staticmethod_list.append(new_staticmethod)

        new_staticmethod_name_to_staticmethod_list_dict[staticmethod_name] = new_staticmethod_list
    
    # new_property_name_to_property_type_annotation_dict
    new_property_name_to_property_type_annotation_dict = dict()

    for property_name, property_type_annotation in class_definition.property_name_to_property_type_annotation_dict.items():
        new_property_name = property_name

        new_property_type_annotation = replace_type_variables_in_type_annotation(
            property_type_annotation,
            old_type_variable_to_new_type_annotation_dict,
            indent_level + 1
        )

        new_property_name_to_property_type_annotation_dict[new_property_name] = new_property_type_annotation
    
    return ClassDefinition(new_type_variable_list, new_method_name_to_method_list_dict, new_staticmethod_name_to_staticmethod_list_dict, new_property_name_to_property_type_annotation_dict)
