from pathlib import Path

from matplotlib import pyplot as plt

CONFIG_DIR = Path(__file__).parent

DIR_BASE = CONFIG_DIR.parent.as_posix()
CONFIG_SCENE = f"{DIR_BASE}/config/scene.yaml"
CONFIG_DELEGATION = f"{DIR_BASE}/config/delegation.yaml"
DIR_TESTCASE = f"{DIR_BASE}/assets/testcase"


def close_figure(event):
    if event.key == 'escape':
        plt.close(event.canvas.figure)


def s(img, title=""):
    plt.imshow(img)
    plt.title(title)
    plt.show()
