import re
from typing import Union, List, Dict

import cv2
from Levenshtein import ratio
from paddleocr import PaddleOCR

from games.azur_lane.config import CONFIG_DELEGATION
from games.azur_lane.interface.scene.asset_manager import am
from lib.dummy_paddleocr import load_recognizer
from util import gen_key
from util.game_cv import match_multi_template, debug_show
from util.io import load_yaml

re.search(r".*?(\D+)", "123:A").group(1)

match_multi_template_ = debug_show(match_multi_template)


class Resource:
    __slots__ = ("name", "min", "max", "rank", "chance")

    def __init__(self, name, min_, max_=None, rank=0, chance=False):
        self.name = name
        self.min = min_
        self.max = max_ if max_ is not None else min_
        self.rank = rank
        self.chance = chance

    def __repr__(self):
        s = f"{self.name}"
        if isinstance(self.rank, int) and self.rank > 0:
            s += f"(T{self.rank})"
        elif isinstance(self.rank, str):
            s += self.rank

        if self.chance:
            s += "[?]"

        s = f"{s}: {self.min}" if self.min == self.max else f"{s}: {self.min}~{self.max}"
        return s


class Delegation:
    __slots__ = ("name", "rank", "level", "duration", "exp", "rewards", "oil_cost", "time_limit", "id")

    pattern_name_rank = re.compile(r"(V?I*V?)?(\w*)")

    def __init__(self, name: str, level: int, duration: str, exp: 0, *rewards: Resource, oil_cost=0, time_limit=None):
        self.name = name
        self.rank = self.pattern_name_rank.match(name[::-1]).group(1)[::1]
        self.level = level
        self.duration = tuple(int(time_parts) for time_parts in duration.split(":", maxsplit=2))
        self.exp = exp
        self.rewards = rewards
        self.oil_cost = oil_cost
        self.time_limit = time_limit
        self.id = gen_key(self.name, self.level, self.time_limit, self.rewards)

    def __repr__(self):
        info = f"{self.name}(lv:{self.level}; duration: {self.duration[0]:0>2}:{self.duration[1]:0>2})" \
               f"\n    {self.rewards}"
        return info


def parse_resource_value(name: str, value: Union[List, str]) -> Resource:
    if len(splits := name.split("_")) == 2:
        res_name, res_rank = splits[0], splits[1]
        if res_rank.startswith("T"):
            res_rank = int(res_rank[1:])
    else:
        res_name, res_rank = name, 0

    chance = False
    if isinstance(value, list):
        min_, max_ = value
    elif isinstance(value, str):
        min_ = max_ = int(value[1:]) if len(value) > 1 else None
        chance = value.startswith("?")
    else:
        min_ = max_ = 0

    return Resource(name=res_name, min_=min_, max_=max_, rank=res_rank, chance=chance)


def parse_delegation_dict(delegation: Dict) -> Delegation:
    resources = sorted(
        (parse_resource_value(k, v) for k, v in delegation.items()
         if k not in {"Name", "Duration", "Level", "Exp", "OilCost", "TimeLimit"}),
        key=lambda res: res.name
    )

    res = Delegation(
        delegation["Name"], delegation["Level"], delegation["Duration"], delegation["Exp"], *resources,
        oil_cost=delegation.get("OilCost", 0), time_limit=delegation.get("TimeLimit"),
    )
    return res


class Parser:
    templates = {
        "label_level": am.template("Popup_Commission.Scene_DelegationList.Label_Level"),
        "label_processing": am.template("Popup_Commission.Scene_DelegationList.Label_Level.Label_Processing"),
    }
    ocr_paddle_numeric = load_recognizer()
    ocr_paddle = PaddleOCR(show_log=False)
    rel_pos = {  # relative to label level
        "label_level": {
            "label_time_limit": (-75, 132, 140, 40),
            # "label_time_limit": (-75, 132,),
        },
        "label_mission": {
            "label_mission_name": (200, 20, 290, 36)
        }
    }
    DELEGATIONS = sum([
        [parse_delegation_dict(v) for v in values]
        for key, values in load_yaml(CONFIG_DELEGATION).items() if key != "__Proto__"],
        start=[]
    )

    @classmethod
    def parse_label_level_locs(cls, image_ori):
        locs = match_multi_template(
            image_ori, cls.templates["label_level"], method=cv2.TM_CCOEFF_NORMED, thresh=.85, thresh_dedup=50
        )
        return locs

    @classmethod
    def parse_time_limit(cls, image_ori, locs=None):
        """

        Args:
            image_ori:
            locs:

        Returns:

        """
        locs = cls.parse_label_level_locs(image_ori) if locs is None else locs

        # use label level as an anchor, to locate other components
        x_rel, y_rel, width, height = cls.rel_pos["label_level"]["label_time_limit"]

        for loc in locs:
            if (top := loc[1] + y_rel) + 180 > image_ori.shape[0]:  # excess the bolder of y-axis
                continue

            sub_image = image_ori[top: top + height, (left := loc[0] + x_rel): left + width]
            if len(sub_image) == 0:
                continue

            # preprocess
            _, sub_image_processed = cv2.threshold(
                cv2.cvtColor(sub_image, cv2.COLOR_RGB2GRAY),
                thresh=210, maxval=255, type=cv2.THRESH_BINARY_INV
            )
            sub_image_processed = cv2.cvtColor(sub_image_processed, cv2.COLOR_GRAY2RGB)
            text, confidence = cls.ocr_paddle.ocr(sub_image_processed, det=False, cls=False)[0]
            text_rectified = f"{text[:2]}:{text[2:4]}:{text[4:6]}" if len(text := re.sub(r"\D", "", text)) == 6 else ""
            yield text_rectified

    @classmethod
    def parse_status(cls, image_ori, locs=None, thresh=.9) -> bool:
        """

        Args:
            image_ori:
            locs:
            thresh:

        Returns:

        """
        locs = cls.parse_label_level_locs(image_ori) if locs is None else locs

        # use label level as an anchor, to locate other components
        x_rel, y_rel = am.rel_image_rect("Popup_Commission.Scene_DelegationList.Label_Level.Label_Processing")
        height, width = cls.templates["label_processing"].shape[:2]
        for loc in locs:
            match_ratio = cv2.matchTemplate(
                image_ori[(top := loc[1] + y_rel): top + height, (left := loc[0] + x_rel): left + width],
                cls.templates["label_processing"], cv2.TM_CCOEFF_NORMED)
            yield match_ratio > thresh

    @classmethod
    def find_most_similar_delegation(cls, ocr_res):
        val_max = 0
        res = None
        for phrase in (x.name for x in cls.DELEGATIONS):
            if (val_cur := ratio(ocr_res, phrase)) >= val_max:
                val_max = val_cur
                res = phrase
        return res, val_max


if __name__ == '__main__':
    from pathlib import Path
    from games.azur_lane.config import DIR_TESTCASE

    dir_test = Path(f"{DIR_TESTCASE}/commission/delegation_list/label_time_limit")
    test_values = load_yaml(dir_test / "test_values.yaml")
    for file_name, values in test_values.items():
        img = cv2.imread(f"{dir_test}/{file_name}")[:, :, ::-1]
        parsed_values = Parser.parse_time_limit(img)
        Parser.parse_label_level_locs(img)
        Parser.parse_status(img)
        for value, parsed_value in zip(values["time_limit"], parsed_values):
            try:
                assert value == parsed_value
                print(f"PASS: {value, parsed_value}")
            except AssertionError:
                print(f"FAILED: {value, parsed_value}")
