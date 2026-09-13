
import json

from dict_list_manager import DictListManager

def find_unserializable(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_unserializable(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            find_unserializable(v, f"{path}[{i}]")
    else:
        try:
            json.dumps(obj, cls=DictListManager.Encoder)
        except TypeError:
            print(f"NOT SERIALIZABLE at {path}: {type(obj)} = {obj!r}")