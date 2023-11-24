from box import Box
import yaml
from collections.abc import Mapping
from copy import deepcopy


class ENAConfig:
    __config = None

    @classmethod
    def current(cls):
        if cls.__config is None:
            with open("config.yml", "r") as cf:
                cls.__config = Box(yaml.load(cf, Loader=yaml.FullLoader))

        return cls.__config


def merge(dict1, dict2):
    """Return a new dictionary by merging two dictionaries recursively."""

    result = deepcopy(dict1)

    for key, value in dict2.items():
        if isinstance(value, Mapping):
            result[key] = merge(result.get(key, {}), value)
        else:
            result[key] = deepcopy(dict2[key])

    return result
