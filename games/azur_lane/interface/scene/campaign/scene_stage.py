import time
from typing import Union

import cv2

from games.azur_lane.interface.scene.asset_manager import am
from games.azur_lane.interface.scene.base import Scene, goto_scene_main, ocr_paddle, auto_retry
from games.azur_lane.interface.scene.name import Namespace
from util.game_cv import slice_image, binarize, find_most_match

__all__ = [
    "SceneCampaignChapter", "PopupStageInfo", "PopupFleetSelection", "PopupFleetSelectionArbitrate",
    "PopupFleetSelectionFixed", "PopupFleetSelectionDuty", "PopupRescueSOS"
]


class SceneCampaignChapter(Scene):
    name = Namespace.scene_campaign_chapter
    map_chapter_names = {
        "虎!虎!虎!": 1,
        "玻瑚海首秀": 2,
        "決戰中途島": 3,
        "所羅門的噩夢上": 4,
        "所羅門的噩夢中": 5,
        "所羅門的噩夢下": 6,
        "混沌之夜": 7,
        "科曼多爾海戰": 8,
        "庫拉灣海戰": 9,
        "科隆班加拉島夜戰": 10,
        "奧古斯塔皇后灣海戰": 11,
        "馬里亞納風雲上": 12,
        "馬里亞納風雲下": 13,
    }
    unique_chars = "".join(sorted(set("".join(map_chapter_names.keys()))))
    chapter_no = None

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "CampaignChapter.Button_DailyTask",
            "CampaignChapter.Label_WeighAnchor",
            "Main.Icon_Resources.Icon_Oil",
            "Main.Icon_Resources.Icon_Money",
            "Main.Icon_Resources.Icon_Diamond",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def recognize_chapter_title(cls, window) -> Union[int, None]:
        chapter_title = cls._recognize_chapter_title(window)
        cls.chapter_no = None or cls.map_chapter_names.get(chapter_title)
        return cls.chapter_no

    @classmethod
    @auto_retry(max_retry=20, retry_interval=.15)
    def _recognize_chapter_title(cls, window) -> Union[int, None]:
        x, y, w, h = am.get_image_xywh("CampaignChapter.Chapters.ChapterNo")
        image_processed = slice_image(binarize(window.screenshot(x, y, w, h), thresh=128))

        ocr_paddle.set_valid_chars(cls.unique_chars)
        ocr_text = ocr_paddle(cv2.cvtColor(image_processed, cv2.COLOR_GRAY2RGB))[0][0]
        res = find_most_match(ocr_text, cls.map_chapter_names.keys())[0]
        if res is None:
            raise ValueError
        return res

    @classmethod
    def open_stage_popup(cls, window, chapter_no=None):
        window.left_click(am.rect(f"CampaignChapter.Chapters.Stages.{chapter_no}"))

    @classmethod
    def go_back_to_anchor_aweigh(cls, window):
        window.left_click(am.rect("CampaignChapter.Chapters.Button_BackToAnchorAweigh"))

    ways = {
        Namespace.scene_main: goto_scene_main,
        Namespace.scene_anchor_aweigh: goto_scene_main,
        Namespace.popup_stage_info: open_stage_popup
    }


class PopupStageInfo(Scene):
    name = Namespace.popup_stage_info

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "PopupStageInfo.Label_WeighAnchor",
            "PopupStageInfo.Button_ImmediateStart",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_immediate_start(cls, window):
        window.left_click(am.rect("PopupStageInfo.Button_ImmediateStart"), sleep=1)

    @staticmethod
    def close_popup(window):
        window.left_click(am.rect("PopupStageInfo.Button_Close"), sleep=1)

    @classmethod
    def is_automation(cls, window) -> bool:
        lt, rb = am.rect("PopupStageInfo.Button_Automation")
        mid = tuple(int((lt[i] + rb[i]) / 2) for i in range(2))
        rgb_tuple = window.pixel_from_window(*mid, as_int=False)

        return rgb_tuple[0] > 100

    @classmethod
    def set_automation(cls, window, turn_on=True, sleep=1):
        if turn_on is not cls.is_automation(window):
            window.left_click(am.rect("PopupStageInfo.Button_Automation"), sleep=1)
        time.sleep(sleep)

    ways = {
        Namespace.scene_campaign: close_popup,
        Namespace.popup_fleet_selection: goto_immediate_start,
        Namespace.popup_fleet_selection_arbitrate: goto_immediate_start,
        Namespace.popup_fleet_selection_fixed: goto_immediate_start,
    }


class PopupFleetSelection(Scene):
    name = Namespace.popup_fleet_selection

    is_fleet_fixed = None

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "PopupFleetSelect.Label_FleetSelect",
            "PopupFleetSelect.Label_Marine",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_immediate_start(cls, window):
        window.left_click(am.rect("PopupFleetSelect.Button_ImmediateStart"), sleep=1)

    @classmethod
    def goto_fleet_duty(cls, window):
        window.left_click(am.rect("PopupFleetSelect.Button_ChangeDuty"), sleep=1)

    @classmethod
    def close(cls, window):
        window.left_click(am.rect("PopupFleetSelect.Button_Close"), sleep=1)

    @classmethod
    def _is_fixed_fleet(cls, window):
        points_to_check = am.eigens(
            "PopupFleetSelect.Button_ChangeFormation",
        )
        return cls.compare_with_pixels(window, points_to_check)

    ways = {
        Namespace.scene_campaign_chapter: close,
        Namespace.scene_campaign: goto_immediate_start,
        Namespace.popup_fleet_selection_duty: goto_fleet_duty,
    }


class PopupFleetSelectionArbitrate(PopupFleetSelection):
    name = Namespace.popup_fleet_selection_arbitrate
    map_fleet_no = dict(zip(range(1, 7), (f"Button_Fleet{x}" for x in ("One", "Two", "Three", "Four", "Five", "Six"))))

    is_fleet_fixed = False

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        return (not cls._is_fixed_fleet(window)) and super().at_this_scene_impl(window)

    @classmethod
    def choose_team(cls, window, team_one=None, team_two=None):
        btn = "PopupFleetSelect.Formation"

        if (key := cls.map_fleet_no.get(team_one)) is not None:
            window.left_click(am.rect(f"{btn}.Button_ChooseTeamOne"), sleep=.5)
            window.left_click(am.rect(f"{btn}.Button_ChooseTeamOne.{key}"), sleep=.5)

        if (key := cls.map_fleet_no.get(team_two)) is not None:
            window.left_click(am.rect(f"{btn}.Button_ChooseTeamTwo"), sleep=.5)
            window.left_click(am.rect(f"{btn}.Button_ChooseTeamTwo.{key}"), sleep=1)


class PopupFleetSelectionFixed(PopupFleetSelection):
    name = Namespace.popup_fleet_selection_fixed

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_fleet_fixed = True

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        return cls._is_fixed_fleet(window) and super().at_this_scene_impl(window)


class PopupFleetSelectionDuty(PopupFleetSelection):
    name = Namespace.popup_fleet_selection_duty

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        duties = cls.show_duty(window)

        return duties != 0b0 and super().at_this_scene_impl(window)

    @classmethod
    def show_duty(cls, window):
        btn = "PopupFleetSelect.Button_ChangeDuty"
        res = 0b0

        s0, s1 = (
            cls.compare_with_pixels(window, am.eigens(f"{btn}.Submarine.{state}"))
            for state in ("Button_AutoEngage", "Button_StandBy")
        )
        if s0 and (not s1):
            res |= 0b1
        elif (not s0) and s1:
            res |= (0b1 << 1)

        for idx, state in enumerate(
                ("Button_StandBy", "Button_AllBattle", "Button_Flagship", "Button_NormalBattle"), start=2
        ):
            if cls.compare_with_pixels(window, am.eigens(f"{btn}.NormalFleet.{state}")) is True:
                res |= (0b1 << idx)

        return res

    @classmethod
    def set_duty_marine(cls, window, team_one) -> bool:
        btn_marine = am.resolve("PopupFleetSelect.Button_ChangeDuty.NormalFleet")
        duty_marines = {
            0b1000: btn_marine["Button_NormalBattle"],
            0b0100: btn_marine["Button_Flagship"],
            0b0010: btn_marine["Button_AllBattle"],
            0b0001: btn_marine["Button_StandBy"],
        }
        if (duty_marine := duty_marines.get(team_one)) is None:
            return False
        window.left_click(duty_marine, sleep=.75)
        return (cls.show_duty(window) >> 2) == team_one

    @classmethod
    def set_duty_submarine(cls, window, team_submarine=0b01) -> bool:
        btn_submarine = am.resolve("PopupFleetSelect.Button_ChangeDuty.Submarine")
        duty_submarines = {
            0b10: btn_submarine["Button_AutoEngage"],
            0b01: btn_submarine["Button_StandBy"],
        }
        if (duty_submarine := duty_submarines.get(team_submarine)) is None:
            return False
        window.left_click(duty_submarine, sleep=.75)
        return (cls.show_duty(window) & 0b000011) == duty_submarine


class SceneCampaignChapter03(SceneCampaignChapter):
    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        return super().at_this_scene_impl(window) and cls._recognize_chapter_title(window=window) == 3


class PopupRescueSOS(Scene):
    name = Namespace.popup_rescue_sos

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "AnchorAweigh.Button_RescueSOS.Popup_RescueSOS",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_scene_anchor_aweigh(cls, window):
        window.left_click(am.rect("AnchorAweigh.Button_RescueSOS.Popup_RescueSOS.Button_GoBack"), sleep=1)

    @classmethod
    def is_signal_found(cls, window):
        points_to_check = am.eigens(
            "AnchorAweigh.Button_RescueSOS.Popup_RescueSOS.Button_Chapter03.State_SignalFound",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_scene_chapter03(cls, window):
        window.left_click(am.rect("AnchorAweigh.Button_RescueSOS.Popup_RescueSOS.Button_Chapter03"), sleep=1.5)

    ways = {
        Namespace.scene_main: goto_scene_main,
        Namespace.scene_anchor_aweigh: goto_scene_anchor_aweigh,
        Namespace.scene_campaign_chapter: goto_scene_chapter03,
    }
