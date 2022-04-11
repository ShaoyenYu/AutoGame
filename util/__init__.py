from hashlib import md5
from pickle import dumps

from util.logging import *


def gen_key(*args, **kwargs):
    return md5(dumps((args, kwargs))).hexdigest()
