from .asset_manager import am
from .base import Scene, SceneUnknown
from .campaign import *
from .delegation import *
from .login import *
from .main import *
from .name import Namespace

SCENES_REGISTERED = {
    x.name: x for x in globals().values() if type(x) is Scene.__class__ and issubclass(x, Scene)
}
