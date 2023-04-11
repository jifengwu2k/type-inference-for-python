from attrs import define


@define
class FunctionDefinition:
    type_variable_list: list
    parameter_type_annotation_list: list
    # new
    # support args.vararg
    vararg_type_annotation: object
    # new
    # support args.kwonlyargs
    kwonlyargs_name_to_type_annotation_dict: dict
    # new
    # support args.kwarg
    kwarg_type_annotation: object
    return_value_type_annotation: object

