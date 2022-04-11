from pathlib import Path

CONFIG_DIR = Path(__file__).parent

DIR_BASE = CONFIG_DIR.parent.as_posix()
DIR_INTERFACE = f"{DIR_BASE}/interface"
DIR_TESTCASE = f"{DIR_BASE}/assets/testcase"

CONFIG_SCENE = f"{DIR_INTERFACE}/scene.yaml"
CONFIG_DELEGATION = f"{DIR_INTERFACE}/delegation.yaml"
