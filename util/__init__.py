import time
from hashlib import md5
from pathlib import Path
from pickle import dumps

from util.logging import *


def gen_key(*args, **kwargs):
    return md5(dumps((args, kwargs))).hexdigest()


def safe_get_dir(path):
    (path := Path(path)).mkdir(parents=True, exist_ok=True)
    return path.as_posix()


def auto_retry(max_retry, retry_interval=.1):
    def _auto_retry(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except:
                for _ in range(max_retry):
                    try:
                        return f(*args, **kwargs)
                    except:
                        time.sleep(retry_interval)
                        continue
                return None

        return wrapper

    return _auto_retry
