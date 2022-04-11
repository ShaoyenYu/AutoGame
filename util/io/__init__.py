import inspect
from pathlib import Path

from yaml import load, CLoader


def get_caller_directory():
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    file = module.__file__
    return Path(file).parent


def load_yaml(file):
    with open(file, encoding="utf-8") as f:
        return load(f, CLoader)
