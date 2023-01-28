from .base import BaseTask
from .auto_login import *
from .farm_campaign_special import *
from .farm_chapter import *
from .farm_submarine import *

TASKS_REGISTERED = {
    x.name: x for x in globals().values()
    if type(x) is type and issubclass(x, BaseTask) and getattr(x, "name") != ""
}
