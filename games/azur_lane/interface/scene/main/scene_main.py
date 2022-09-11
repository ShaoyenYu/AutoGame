import re

import cv2
import numpy as np
from cv2 import TM_SQDIFF_NORMED

from games.azur_lane.interface.scene.asset_manager import am
from games.azur_lane.interface.scene.base import Scene, auto_retry, goto_scene_main
from games.azur_lane.interface.scene.name import Namespace
from lib.dummy_paddleocr import load_recognizer
from util.game_cv import match_multi_template, binarize, debug_show
from util.game_cv.ocr import ocr_int, ocr_preprocess

__all__ = ["SceneMain", "PopupCommission", "SceneAnchorAweigh"]


class SceneMain(Scene):
    name = Namespace.scene_main

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Main.Icon_Resources.Icon_Oil",
            "Main.Icon_Resources.Icon_Money",
            "Main.Icon_Resources.Icon_Diamond",
            "Main.Button_AnchorAweigh",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_scene_anchor_aweigh(cls, window):
        window.left_click(am.rect("Main.Button_AnchorAweigh"), sleep=1.5)

    @classmethod
    def goto_popup_commission(cls, window):
        window.left_click(am.rect("Main.Button_Commission.Popup_Commission"), sleep=1.5)

    @classmethod
    def open_popup_living_area(cls, window):
        window.left_click(am.rect("Main.Button_LivingArea"))

    @classmethod
    def has_new_notice(cls, window):
        asset = "Main.Button_LivingArea.State_HasNewNotice"
        return cls.compare_with_template(window, am.image_rect(asset), am.template(asset), .8)

    ways = {
        Namespace.scene_anchor_aweigh: goto_scene_anchor_aweigh,
        Namespace.popup_commission: goto_popup_commission,
    }


class PopupCommission(Scene):
    name = Namespace.popup_commission
    ocr_int = load_recognizer()
    ocr_int.set_valid_chars("0123456789完成前往:")

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Main.Button_Commission.Popup_Commission.Label_Commission",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def is_commissions_all_folded(cls, window):
        points_to_check = am.eigens(
            "Main.Button_Commission.Popup_Commission.State_AllFolded",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def open_delegation_popup(cls, window):
        window.left_drag((280, 340), (280, 940), duration=.25, interval=.025, sleep=.5)
        window.left_click(am.rect("Popup_Commission.Popup_Delegation"), sleep=.5)
        window.left_drag((490, 900), (490, 700), duration=.25, interval=.025, sleep=1)

    @classmethod
    def parse_delegation_summary(cls, window):
        template = am.template("Popup_Commission.Popup_Delegation.Label_RightBottomAnchor")
        x_rb_area, y_rb_area, w_rb_area, h_rb_area = am.get_image_xywh(
            "Popup_Commission.Popup_Delegation.Label_RightBottomAnchor")
        image_ori = window.screenshot(x_rb_area, y_rb_area, w_rb_area, h_rb_area)

        positions = match_multi_template(image_ori, template, thresh=.9, thresh_dedup=20)

        @auto_retry(max_retry=20, retry_interval=.25)
        def _parse_remaining_time(x_anchor, y_anchor):
            rel_x_rt, rel_y_rt, w_rt, h_rt = am.rel_image_rect(
                "Popup_Commission.Popup_Delegation.Label_RightBottomAnchor.Label_RemainingTime")
            rel_x_cp, rel_y_cp, w_cp, h_cp = am.rel_image_rect(
                "Popup_Commission.Popup_Delegation.Label_RightBottomAnchor.Button_Complete")

            x_base, y_base = x_rb_area + x_anchor, y_rb_area + y_anchor
            image = window.screenshot(x_base + rel_x_rt, y_base + rel_y_rt, w_rt, h_rt)
            image_processed = binarize(image, thresh=155)
            text = cls.ocr_int(cv2.cvtColor(image_processed, cv2.COLOR_GRAY2RGB))[0][0]

            text = re.sub(r":+", r":", text)  # rectify if ":" appears more than once

            if len(split := text.split(r":")) != 3:
                image = window.screenshot(x_base + rel_x_cp, y_base + rel_y_cp, w_cp, h_cp)
                text = cls.ocr_int(image)[0][0]
                if text not in ("完成", "前往"):
                    raise ValueError(f"wrong text: {text}")
            else:
                if any((len(x) != 2 for x in split)):
                    raise ValueError(f"wrong time format: {split}")
            return text

        # for i in range(60):
        #     print(f"test <{i}>")
        #     for rel_x_rb, rel_y_rb in positions:
        #         text_remaining_time = _parse_remaining_time(rel_x_rb, rel_y_rb)
        #         print(text_remaining_time)
        #     print("=" * 64)
        #     time.sleep(1)

        for rel_x_rb, rel_y_rb in positions:
            text_remaining_time = _parse_remaining_time(rel_x_rb, rel_y_rb)
            print(text_remaining_time)
            return text_remaining_time

    @classmethod
    def goto_tactic_academy(cls):
        pass

    @classmethod
    def goto_tech_academy(cls):
        pass

    @classmethod
    def detect_delegation_summary(cls, window):
        from matplotlib import pyplot as plt
        def s(i):
            plt.imshow(i)
            plt.show()

        match_multi_template_ = debug_show(match_multi_template)

        template = am.template("Scene_DelegationList.Label_Mission")
        image = window.screenshot()
        q = match_multi_template_(image, template, method=TM_SQDIFF_NORMED, threshold=.01)

        x_rel, y_rel = 282, 34
        width, height = 144, 44

        for x, y in q:
            image = window.screenshot(x + x_rel, y + y_rel, width, height)
            a2 = np.where(np.where(image < 230, 255, 0) != 255, 0, 255).astype(image.dtype)
            res = ocr_int(a2, config="--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789:", lang="eng")
            print(res)


class SceneAnchorAweigh(Scene):
    name = Namespace.scene_anchor_aweigh

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "AnchorAweigh.Icon_Resources.Icon_Oil",
            "AnchorAweigh.Icon_Resources.Icon_Money",
            "AnchorAweigh.Icon_Resources.Icon_Diamond",
            "AnchorAweigh.Button_MainBattleLine",
            "AnchorAweigh.Label_WeighAnchor",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_scene_campaign_chapter(cls, window):
        window.left_click(am.rect("AnchorAweigh.Button_MainBattleLine"), sleep=1)

    @classmethod
    def open_popup_rescue_sos(cls, window):
        window.left_click(am.rect("AnchorAweigh.Button_RescueSOS"), sleep=1)

    @classmethod
    @auto_retry(max_retry=20, retry_interval=.15)
    def recognize_rescue_times(cls, window):
        x, y, w, h = am.get_image_xywh("AnchorAweigh.Button_RescueSOS")
        image = window.screenshot(x, y, w, h)
        res = int(ocr_int(ocr_preprocess(image), config="--psm 8 --oem 3 -c tessedit_char_whitelist=012345678")[0])
        return res

    ways = {
        Namespace.scene_main: goto_scene_main,
        Namespace.scene_campaign_chapter: goto_scene_campaign_chapter,
        Namespace.popup_rescue_sos: open_popup_rescue_sos
    }
