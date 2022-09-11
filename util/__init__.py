from hashlib import md5
from pathlib import Path
from pickle import dumps

from util.logging import *


def gen_key(*args, **kwargs):
    return md5(dumps((args, kwargs))).hexdigest()


def safe_get_dir(path):
    (path := Path(path)).mkdir(parents=True, exist_ok=True)
    return path.as_posix()
