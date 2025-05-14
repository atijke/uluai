import json
import telethon
from bson import json_util
from copy import copy


def telethon_object_formatted(data):
    if not data:
        return data

    try:
        return json.loads(data.to_json())
    except (Exception,):
        data_dict = data.to_dict()

        for data_key in list(data_dict):
            if to_dict_func := getattr(data_dict[data_key], "to_dict", None):
                if callable(to_dict_func):
                    data_dict[data_key] = data_dict[data_key].to_dict()

        return data_dict


def telethon_event_object_to_dict(data):
    try:
        data_dict = data.to_dict()

        for data_key in list(data_dict):
            if to_dict_func := getattr(data_dict[data_key], "to_dict", None):
                if callable(to_dict_func):
                    data_dict[data_key] = data_dict[data_key].to_dict()

        return data_dict

    except (Exception,):
        return None


def list_bson_formatted(data: list):
    return json.loads(json_util.dumps(data))


def dict_bson_formatted(data: dict):
    return json.loads(json_util.dumps(data))


def tl_object_from_dict(input_data):
    input_copy = copy(input_data)

    if not input_copy or not isinstance(input_copy, dict) or '_' not in input_copy:
        return input_copy

    for input_dict_key in input_copy:
        input_copy[input_dict_key] = tl_object_from_dict(input_copy[input_dict_key])

    obj_type_str = copy(input_copy['_'])

    del input_copy['_']

    obj_type_str_split = obj_type_str.split('.')

    if len(obj_type_str_split) == 1:
        tl_object_class = getattr(telethon.tl.types, obj_type_str, getattr(telethon.types, obj_type_str))
    else:
        tl_object_class = getattr(getattr(telethon.events, obj_type_str_split[0]), obj_type_str_split[1])

    obj = tl_object_class(**input_copy)

    return obj

