import time
from typing import Optional

import numpy as np
from cv2 import TM_SQDIFF_NORMED

from games.azur_lane.interface.scene.asset_manager import am
from games.azur_lane.interface.scene.base import Scene, goto_scene_main, auto_retry
from games.azur_lane.interface.scene.name import Namespace
from util.game_cv import match_multi_template, combine_similar_points
from util.game_cv.ocr import ocr_int, ocr_preprocess

__all__ = [
    "SceneCampaign", "PopupCampaignInfo", "PopupInfoAutoBattle", "PopupGetShip", "SceneGetItems", "PopupCampaignReward",
    "PopupCampaignRewardWithMeta",
]


class SceneCampaign(Scene):
    name = Namespace.scene_campaign

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Campaign.Label_LimitTime",
            "Campaign.Label_WeighAnchor",
            "Main.Icon_Resources.Icon_Oil",
            "Main.Icon_Resources.Icon_Money",
            "Main.Icon_Resources.Icon_Diamond",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def is_automation_on(cls, window) -> bool:
        button = "Campaign.Button_Automation"
        return cls.compare_with_template(window, am.rect(button), am.template(f"{button}.State_On"), threshold=.999)

    @classmethod
    def is_automation_off(cls, window) -> bool:
        button = "Campaign.Button_Automation"
        return cls.compare_with_template(window, am.rect(button), am.template(f"{button}.State_Off"), threshold=.999)

    @classmethod
    def is_formation_locked(cls, window):
        points_to_check = am.eigens("Campaign.Button_FormationLock.State_On")
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def is_strategy_popup(cls, window):
        points_to_check = am.eigens(
            "Campaign.Button_Strategy.State_Expanded"
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    @auto_retry(max_retry=20, retry_interval=.25)
    def recognize_fleet_no(cls, window) -> int:
        x, y, w, h = am.get_image_xywh("Campaign.Label_FleetNo")
        image = window.screenshot(x, y, w, h)
        return int(ocr_int(ocr_preprocess(image), config="--psm 8 --oem 3 -c tessedit_char_whitelist=1234").strip())

    @classmethod
    def get_fleet_formation(cls, window) -> Optional[str]:
        if cls.is_strategy_popup(window):
            for state in ("State_SingleLineAssault", "State_DoubleLineAdvance", "State_CircularDefense"):
                points_to_check = am.eigens(
                    f"Campaign.Button_Strategy.State_Expanded.Button_SwitchFormation.{state}"
                )
                if cls.compare_with_pixels(window, points_to_check):
                    return state
        return None

    @staticmethod
    def detect_enemy_impl(img_screen, templates, threshold=.1, method=TM_SQDIFF_NORMED):
        res = []
        for img_template in templates:
            res.extend(list(match_multi_template(img_screen, img_template, thresh=threshold, method=method)))

        if len(res) > 0:
            res = combine_similar_points(np.array(res))

        return res

    @classmethod
    def detect_enemy(cls, window, scale, img_screen=None, threshold=.1, method=TM_SQDIFF_NORMED):
        if img_screen is None:
            img_screen = window.screenshot()

        templates = [am.template(x) for x in am.resolve(f"Campaign.Enemy.Scale.{scale}", "Images").values()]
        res = cls.detect_enemy_impl(img_screen, templates, threshold, method)
        if len(res) > 0 and scale != "Boss":
            res += np.array([50, 80])
        else:
            if len(res) == 1:
                res += np.array([30, 30])
        return list(res)

    @classmethod
    def attack_enemies(cls, window):
        img_screen_1 = window.screenshot()
        time.sleep(1.5)
        img_screen_2 = window.screenshot()
        enemy_type = {4: "Boss", 3: "Large", 2: "Medium", 1: "Small"}
        enemies = {
            k: cls.detect_enemy(window, v, img_screen_1)
            for k, v in enemy_type.items()
        }
        for k, v in enemy_type.items():
            enemies[k].extend(cls.detect_enemy(window, v, img_screen_2))
            if len(enemies[k]) > 0:
                enemies[k] = combine_similar_points(np.array(enemies[k]))
        print(enemies)
        for k in (4, 3, 2, 1):
            if len(enemies_found := enemies[k]) > 0:
                window.left_click(tuple(enemies_found[0]), sleep=1)
                return True
        return False

    ways = {
        Namespace.scene_main: goto_scene_main
    }


class PopupCampaignInfo(Scene):
    name = Namespace.popup_campaign_info

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Campaign.Popup_Information",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_campaign(cls, window):
        window.left_click(am.rect("Campaign.Popup_Information.Button_Exit"), sleep=.75)

    ways = {
        Namespace.scene_campaign: goto_campaign
    }


class PopupInfoAutoBattle(Scene):
    name = Namespace.popup_info_auto_battle

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Popup_Information.AutoBattle",
            "Popup_Information.AutoBattle.Button_Ensure",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def go_back(cls, window):
        window.left_click(am.rect("Popup_Information.AutoBattle.Button_Ensure"), sleep=.75)

    ways = {
        Namespace.scene_battle_formation: go_back
    }


class PopupGetShip(Scene):
    name = Namespace.popup_get_ship

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Campaign.Popup_GetShip",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_campaign(cls, window):
        window.left_click(am.rect("Campaign.Popup_GetShip.Button_Exit"), sleep=2)

    ways = {
        Namespace.scene_campaign: goto_campaign
    }


class SceneGetItems(Scene):
    name = Namespace.scene_get_items

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check1 = am.eigens(
            "Popup_GetItems.Label_GetItems1",
        )

        points_to_check2 = am.eigens(
            "Popup_GetItems.Label_GetItems2",
        )

        return cls.compare_with_pixels(window, points_to_check1) or cls.compare_with_pixels(window, points_to_check2)

    @classmethod
    def goto_battle_results(cls, window):
        window.left_click((1850, 200), sleep=.5)

    ways = {
        Namespace.scene_battle_result: goto_battle_results
    }


class PopupCampaignReward(Scene):
    name = Namespace.popup_campaign_reward

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "CampaignChapter.Label_TotalRewards_without_META",
            "CampaignChapter.Label_TotalRewards_without_META.Button_GoAgain",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_campaign(cls, window):
        window.left_click((1460, 115), sleep=1.5)  # just a random empty space

    ways = {
        Namespace.scene_campaign: goto_campaign
    }


class PopupCampaignRewardWithMeta(Scene):
    name = Namespace.popup_campaign_reward_meta

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "CampaignChapter.Label_TotalRewards_with_META",
            "CampaignChapter.Label_TotalRewards_with_META.Button_GoAgain",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_campaign(cls, window):
        window.left_click((1850, 300), sleep=1.5)  # just a random empty space

    ways = {
        Namespace.scene_campaign: goto_campaign
    }
