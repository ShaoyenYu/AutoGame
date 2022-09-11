from pathlib import Path

from util.io import get_caller_directory

CONFIG_DIR = get_caller_directory()

DIR_USR_HOME = Path.home().as_posix()
DIR_USR_HOME_PIC = f"{DIR_USR_HOME}/Pictures"
DIR_USR_AUTO_GAME = f"{DIR_USR_HOME_PIC}/AutoGame"
DIR_USR_AUTO_GAME_AZURLANE = f"{DIR_USR_AUTO_GAME}/AzurLane"

DIR_BASE = CONFIG_DIR.parent.as_posix()
DIR_INTERFACE = f"{DIR_BASE}/interface"
DIR_TESTCASE = f"{DIR_BASE}/assets/testcase"

CONFIG_SCENE = f"{DIR_INTERFACE}/ui/scene.yaml"
CONFIG_DELEGATION = f"{DIR_INTERFACE}/ui/delegation.yaml"
