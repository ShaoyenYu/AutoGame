from .base import BaseTask
from .farm_campaign_special import TaskFarmCampaignSpecial
from .farm_chapter import TaskFarmChapter
from .farm_submarine import TaskFarmSubmarineSOS

TASKS_REGISTERED = {
    x.name: x for x in globals().values() if type(x) is BaseTask.__class__ and issubclass(x, BaseTask)
}
