import itertools
import re
import time
from abc import abstractmethod
from functools import lru_cache
from typing import Tuple, Union, Any, Optional

import cv2
import numpy as np
import pytesseract
from Levenshtein import ratio
from cv2 import (
    TM_CCOEFF_NORMED, TM_CCORR_NORMED, TM_SQDIFF, TM_SQDIFF_NORMED,
)
from matplotlib import pyplot as plt
from scipy.spatial import distance_matrix

from games.azur_lane.config import CONFIG_SCENE, DIR_BASE
from games.azur_lane.controller.simulator import AzurLaneWindow
from lib.dummy_paddleocr import load_recognizer
from util.io import load_yaml

ocr_paddle = load_recognizer()


class AssetManager:
    ASSETS = load_yaml(CONFIG_SCENE)

    @staticmethod
    def recur_resolve(dict_, keys):
        res = None
        for key in keys:
            res = dict_ = dict_[key]
        return res

    @classmethod
    def resolve(cls, asset_name, asset_type=None):
        res = cls.recur_resolve(cls.ASSETS, asset_name.split("."))
        if asset_type is None:
            return res
        return res[f"__{asset_type}"]

    @classmethod
    @lru_cache(maxsize=10)
    def rel_image_rect(cls, asset_name: str):
        return cls.resolve(asset_name)["__RelImageRect"]

    @classmethod
    def image(cls, asset_name: str):
        return cls.resolve(asset_name)["__Image"]

    @classmethod
    def image_rect(cls, asset_name: str):
        return cls.resolve(asset_name)["__ImageRect"]

    @classmethod
    def get_image_xywh(cls, asset_name):
        lt, rb = (point[:2] for point in cls.image_rect(asset_name))
        return lt[0], lt[1], rb[0] - lt[0], rb[1] - lt[1]

    @classmethod
    def rect(cls, asset_name: str):
        return cls.resolve(asset_name)["__Rect"][:2]

    @classmethod
    def eigen(cls, asset_name: str):
        return cls.resolve(asset_name)["__Eigen"]

    @classmethod
    def eigens(cls, *objects):
        if isinstance(objects, str):
            objects = [objects]
        return itertools.chain.from_iterable((cls.eigen(xy_rgb) for xy_rgb in objects))

    @classmethod
    @lru_cache(maxsize=10)
    def template(cls, asset_name: str):
        """

        Args:
            asset_name: str
                "/a/b/c", or "a.b.c"

        Returns:

        """
        file_path_relative = cls.image(asset_name) if not asset_name.startswith("/") else asset_name
        return cv2.imread(f"{DIR_BASE}{file_path_relative}")[:, :, ::-1]


am = AssetManager


def match_single_template(origin: np.ndarray, template: np.ndarray, method=TM_CCORR_NORMED, debug=True) -> Tuple[
    Any, Any, Any, Any]:
    result = cv2.matchTemplate(origin, template, method)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if debug:
        origin_copy = origin.copy()
        width, height = template.shape[:2][::-1]
        top_left = max_loc
        bottom_right = (top_left[0] + width, top_left[1] + height)
        cv2.rectangle(origin_copy, top_left, bottom_right, (255, 255, 255), 2)
        plt.imshow(origin_copy)
        plt.show()
    return min_val, max_val, min_loc, max_loc


def debug_show(f):
    def wrapper(img_ori, img_tem, *args, **kwargs):
        locs = f(img_ori, img_tem, *args, **kwargs)

        img_cp = img_ori.copy()
        w, h = img_tem.shape[:2][::-1]
        for pt in locs:
            print(pt)
            cv2.rectangle(img_cp, tuple(pt), (pt[0] + w, pt[1] + h), (255, 0, 0), 5)
        plt.imshow(img_cp)
        plt.show()

        return locs

    return wrapper


def match_multi_template(img_ori: np.ndarray, img_tem: np.ndarray, method=TM_CCOEFF_NORMED, thresh=.8, thresh_dedup=0):
    res = cv2.matchTemplate(img_ori, img_tem, method)
    if method in (TM_SQDIFF, TM_SQDIFF_NORMED):
        loc = np.where(res <= thresh)
    else:
        loc = np.where(res >= thresh)
    locs = np.array([loc[1], loc[0]]).T

    if thresh_dedup > 0 and len(locs) > 0:
        locs = combine_similar_points(locs, threshold=thresh_dedup)

    return list(locs)


def goto_scene_main(window: AzurLaneWindow):
    window.left_click(am.rect("AnchorAweigh.Button_BackToMain"), sleep=1)


def ocr_preprocess(img, k_size=(3, 3)):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, k_size, 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Morph open to remove noise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, k_size)
    final = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    return final


def ocr_int(img, config, lang="eng", preprocess=None):
    if preprocess is not None:
        img = ocr_preprocess(img)
    data = pytesseract.image_to_string(img, lang=lang, config=config)
    return data


def ocr_eng(img, config):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Morph open to remove noise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    final_img = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    cv2.imshow("fi", final_img)

    data = pytesseract.image_to_string(final_img, lang='eng', config=config)
    return data


def ocr_zhtw(img, config):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    data = pytesseract.image_to_string(thresh, lang='chi_tra', config=config)

    return data


def binarize(image: np.ndarray, thresh=127, maxval=255, type=cv2.THRESH_BINARY_INV):
    image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    _, image_bin = cv2.threshold(image_gray, thresh, maxval, type)
    return image_bin


def slice_image(image, redundant_pixel=5):
    left = image.argmin(axis=1)
    right = image[:, ::-1].argmin(axis=1)
    left = left[left > 0].min() - redundant_pixel
    right = image.shape[1] - right[right > 0].min() + redundant_pixel
    return image[:, left: right]


def find_most_match(text, phrases):
    val_max = 0
    most_match = None
    for phrase in phrases:
        if (val_cur := ratio(text, phrase)) >= val_max:
            val_max = val_cur
            most_match = phrase
    return most_match, val_max


def combine_similar_points(points, threshold=50):
    points = np.array(points)
    points_sorted = points[np.lexsort((points[:, 1], points[:, 0]))]
    dm = distance_matrix(points_sorted, points_sorted)
    return points_sorted[np.unique((dm < threshold).argmax(axis=0))]


def auto_retry(max_retry, retry_interval=.1):
    def _auto_retry(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except:
                for _ in range(max_retry):
                    try:
                        return f(*args, **kwargs)
                    except:
                        time.sleep(retry_interval)
                        continue
                return None

        return wrapper

    return _auto_retry


class Namespace:
    popup_info_auto_battle = "Popup.Info.AutoBattle"

    scene_main = "Scene.Main"
    popup_commission = "Popup.Commission"
    scene_delegation_list = "Scene.DelegationList"

    scene_delegation_success = "Scene.Delegation.Success"
    scene_anchor_aweigh = "Scene.AnchorAweigh"
    popup_rescue_sos = "Popup.AnchorAweigh.RescueSOS"
    scene_campaign = "Scene.Campaign"
    popup_campaign_info = "Popup.Campaign.Info"
    scene_battle_formation = "Scene.Battle.Formation"
    scene_battle = "Scene.Battle"
    popup_get_ship = "Popup.GetShip"
    scene_battle_checkpoint_00 = "Scene.Battle.Checkpoint_00"
    scene_battle_checkpoint_01 = "Scene.Battle.Checkpoint_01"
    scene_get_items = "Scene.GetItems"
    scene_battle_result = "Scene.Battle.Result"

    popup_stage_info = "Popup.StageInfo"
    popup_fleet_selection = "Popup.FleetSelection"
    popup_fleet_selection_arbitrate = "Popup.FleetSelectionArbitrate"
    popup_fleet_selection_fixed = "Popup.FleetSelectionFixed"
    popup_fleet_selection_duty = "Popup.FleetSelection.Duty"

    popup_campaign_reward = "Popup.Campaign.Reward"
    popup_campaign_reward_meta = "Popup.Campaign.RewardWithMeta"

    scene_campaign_chapter = "Scene.Campaign.Chapter"


class Scene:
    window = None

    def __init__(self, window: AzurLaneWindow, scene_from=None):
        self.window = window
        self.scene_from = scene_from
        self._bounds = None

    @staticmethod
    def bind_window(f):
        def wrapper(self, window=None, *args, **kwargs):
            window = self.window if window is None else window
            return f(self, window, *args, **kwargs)

        return wrapper

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def bounds(self) -> dict:
        pass

    def at(self, scene):
        return isinstance(self, scene)

    def get_bound_methods(self):
        if self._bounds is None:
            self._bounds = self.bounds
        return self._bounds

    def update_scenes(self, scene_cur, scene_prev=None):
        self.window.scene_prev, self.window.scene_cur = scene_prev or self.window.scene_cur, scene_cur

    def at_this_scene_(self, window: AzurLaneWindow = None):
        window = window if window is not None else self.window
        return self.at_this_scene(window)

    @classmethod
    @abstractmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        """Custom method to implement"""
        pass

    @staticmethod
    def compare_with_pixels(window, pixels, threshold=1, tolerance=0):
        return window.compare_with_pixel(pixels, threshold=threshold, tolerance=tolerance)

    def goto(self, next_scene, sleep=0, *args, **kwargs):
        if (next_scene := scene_names.get(next_scene)) is None:
            has_arrived = False
            print(f"Has arrived: {has_arrived}")
            return has_arrived

        if not self.at_this_scene_():
            print(f"Not here: {self}")
            return False

        self.bounds[next_scene.name](self.window, *args, **kwargs)
        if has_arrived := next_scene.at_this_scene(self.window):
            self.update_scenes(next_scene(self.window))
        else:
            self.window.scene_cur.detect_scene()

        if sleep > 0:
            time.sleep(sleep)
        return has_arrived

    def detect_scene(self):
        if (cur_scene := self._detect_scene(self.window)) is None:
            return cur_scene(self.window)

        self.update_scenes(cur_scene(self.window))
        return self.window.scene_cur

    @classmethod
    def _detect_scene(cls, window):
        for scene in scenes_registered:
            if scene.at_this_scene(window):
                return scene
        return SceneUnknown

    def __repr__(self):
        return f"{self.window} @ {self.name}"


class SceneUnknown(Scene):
    name = "Scene.Unknown"
    bounds = dict()

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        if Scene._detect_scene(window).name == "Scene.Unknown":
            return True
        return False


class SceneMain(Scene):
    name = Namespace.scene_main

    @property
    def bounds(self) -> dict:
        bounds = {
            Namespace.scene_anchor_aweigh: self.goto_scene_anchor_aweigh,
            Namespace.popup_commission: self.goto_popup_commission,
        }
        return bounds

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check_1 = am.eigens(
            "Main.Icon_Resources.Icon_Oil",
            "Main.Icon_Resources.Icon_Money",
            "Main.Icon_Resources.Icon_Diamond",
        )
        points_to_check_2 = am.eigens(
            "Main.Button_AnchorAweigh",
        )
        return cls.compare_with_pixels(window, points_to_check_1, threshold=1) and cls.compare_with_pixels(window, points_to_check_2, tolerance=10)

    @staticmethod
    def goto_scene_anchor_aweigh(window: AzurLaneWindow):
        window.left_click(am.rect("Main.Button_AnchorAweigh"), sleep=1.5)

    @staticmethod
    def goto_popup_commission(window: AzurLaneWindow):
        window.left_click(am.rect("Main.Button_Commission.Popup_Commission"), sleep=1.5)

    @staticmethod
    def open_popup_living_area(window: AzurLaneWindow):
        window.left_click(am.rect("Main.Button_LivingArea"))

    def has_new_notice(self):
        asset = "Main.Button_LivingArea.State_HasNewNotice"
        return self.window.compare_with_template(am.image_rect(asset), am.template(asset), .8)


class PopupCommission(Scene):
    name = Namespace.popup_commission
    ocr_int = load_recognizer()
    ocr_int.set_valid_chars("0123456789完成前往:")

    def bounds(self) -> dict:
        destinations = {}
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "Main.Button_Commission.Popup_Commission.Label_Commission",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @Scene.bind_window
    def is_commissions_all_folded(self, window=None):
        points_to_check = am.eigens(
            "Main.Button_Commission.Popup_Commission.State_AllFolded",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @Scene.bind_window
    def open_delegation_popup(self, window: AzurLaneWindow = None):
        window.left_drag((280, 340), (280, 940), duration=.25, interval=.025, sleep=.5)
        window.left_click(am.rect("Popup_Commission.Popup_Delegation"), sleep=.5)
        window.left_drag((490, 900), (490, 700), duration=.25, interval=.025, sleep=1)

    @Scene.bind_window
    def parse_delegation_summary(self, window: AzurLaneWindow = None):
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
            text = self.ocr_int(cv2.cvtColor(image_processed, cv2.COLOR_GRAY2RGB))[0][0]

            text = re.sub(r":+", r":", text)  # rectify if ":" appears more than once

            if len(split := text.split(r":")) != 3:
                image = window.screenshot(x_base + rel_x_cp, y_base + rel_y_cp, w_cp, h_cp)
                text = self.ocr_int(image)[0][0]
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

    def goto_tactic_academy(self):
        pass

    def goto_tech_academy(self):
        pass

    @staticmethod
    def detect_delegation_summary(window):
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
            # s(a2)
            # print(data)
            res = ocr_int(a2, config="--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789:", lang="eng")
            print(res)


class SceneDelegationList(Scene):
    name = Namespace.scene_delegation_list

    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_main: goto_scene_main
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "Scene_DelegationList.Label_Delegation",
            "Scene_DelegationList.Label_AvailableFleets",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    # def detect_delegations(self):
    #     ocr_paddle = load_recognizer()
    #     from matplotlib import pyplot as plt
    #     from lib.dummy_paddleocr import default_text_recognizer_zhtw
    #     def s(i):
    #         plt.imshow(i)
    #         plt.show()
    #
    #     match_multi_template_ = debug_show(match_multi_template)
    #
    #     template = read_template(ASSETS["Popup_Commission"]["Scene_DelegationList"]["Label_Mission"]["__Image"])
    #     image = self.window.screenshot()
    #     labels_mission = match_multi_template_(image, template, method=TM_CCOEFF_NORMED, threshold=.95)
    #
    #     x_rel, y_rel = -145, 20
    #     width, height = 225, 36
    #     tasks = [
    #         "日常資源開發", "高階戰術研發", "高階科研任務",
    #         "同盟觀艦儀式", "前線基地防衛巡邏", "大型商船護衛",
    #         "I", "V"
    #     ]
    #     white_chars = "".join(set("".join(tasks)))
    #
    #     for x, y in labels_mission:
    #         image_mission_name = image[y + y_rel: y + y_rel + height, x + x_rel: x + x_rel + width]
    #         # image = self.window.screenshot(x + x_rel, y + y_rel, width, height)
    #         a2 = np.where(np.where(image_mission_name < 180, 255, 0) != 255, 0, 255).astype(image_mission_name.dtype)
    #         a3 = cv2.cvtColor(a2, cv2.COLOR_RGB2GRAY)
    #         thresh, a4 = cv2.threshold(a3, 127, 255, cv2.THRESH_BINARY)
    #         bolder = a4.argmin(axis=1)
    #         if not (bolder == 0).all():
    #             bolder = bolder[bolder > 0].min() - 5
    #             a5 = a4[:, bolder:]
    #         else:
    #             continue
    #         # a3 = a2.flatten()
    #         # a4 = np.where((a3 != 0) | (a3 != 255), 0, 255).reshape(a2.shape)
    #         # res = ocr_zhtw(a2, config=f"--psm 7 --oem 1 tessedit_char_whitelist={white_chars} tessedit_char_blacklist=!！嵒")
    #         # res = pytesseract.image_to_string(a4, lang='chi_tra', config=f"--psm 7 --oem 1")
    #         ocr_tesseract = re.sub("\s", "", pytesseract.image_to_string(a5, lang="chi_tra", config=f"--psm 7 --oem 1"))
    #         valid_chars = "|BINVWY主交任保倫假偵備儀前力務卡同員商地型基多大姆委島巡常度式戰接援支救敵日殲波源滅物瑪瓦發盟研礦科級線羅脈船艦萌術衛裝襲要觀解託護資輸運邏部開防隊階高麗馬內"
    #         default_text_recognizer_zhtw.set_valid_chars(valid_chars)
    #         ocr_paddle = default_text_recognizer_zhtw([cv2.cvtColor(a5, cv2.COLOR_BGR2RGB)])[0][0][0]
    #
    #         # res = ocr_zhtw(a2, config=f"--psm 7 --oem 3")
    #
    #         print(ocr_tesseract)
    #         print(ocr_paddle)
    #         continue
    #         # print(data)
    #
    #     pass


class PopupDelegationSuccess(Scene):
    name = Namespace.scene_delegation_success

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_get_items: self.goto_popup_get_items,
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "Main.Button_Commission.Popup_Commission.Popup_DelegationSuccess",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @staticmethod
    def goto_popup_get_items(window: AzurLaneWindow):
        window.left_click(
            am.rect("Main.Button_Commission.Popup_Commission.Delegation.Popup_DelegationSuccess.Button_ExitScene"),
            sleep=1
        )


class SceneAnchorAweigh(Scene):
    name = Namespace.scene_anchor_aweigh

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_main: goto_scene_main,
            Namespace.scene_campaign_chapter: self.goto_scene_campaign_chapter,
            Namespace.popup_rescue_sos: self.open_popup_rescue_sos
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "AnchorAweigh.Icon_Resources.Icon_Oil",
            "AnchorAweigh.Icon_Resources.Icon_Money",
            "AnchorAweigh.Icon_Resources.Icon_Diamond",
            "AnchorAweigh.Button_MainBattleLine",
            "AnchorAweigh.Label_WeighAnchor",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @staticmethod
    def goto_scene_campaign_chapter(window: AzurLaneWindow):
        window.left_click(am.rect("AnchorAweigh.Button_MainBattleLine"), sleep=1)

    @staticmethod
    def open_popup_rescue_sos(window: AzurLaneWindow):
        window.left_click(am.rect("AnchorAweigh.Button_RescueSOS"), sleep=1)

    def recognize_rescue_times(self, max_retry=20):
        x, y, w, h = am.get_image_xywh("AnchorAweigh.Button_RescueSOS")
        image = self.window.screenshot(x, y, w, h)
        try:
            res = int(ocr_int(ocr_preprocess(image), config="--psm 8 --oem 3 -c tessedit_char_whitelist=012345678")[0])
        except:
            res = None
            for _ in range(max_retry):
                if res := self.recognize_rescue_times(max_retry=0) is not None: break
        finally:
            return res


class PopupRescueSOS(Scene):
    name = Namespace.popup_rescue_sos

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_main: goto_scene_main,
            Namespace.scene_anchor_aweigh: self.goto_scene_anchor_aweigh,
            Namespace.scene_campaign_chapter: self.goto_scene_chapter03,
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "AnchorAweigh.Button_RescueSOS.Popup_RescueSOS",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @staticmethod
    def goto_scene_anchor_aweigh(window: AzurLaneWindow):
        window.left_click(am.rect("AnchorAweigh.Button_RescueSOS.Popup_RescueSOS.Button_GoBack"), sleep=1)

    def is_signal_found(self):
        points_to_check = am.eigens(
            "AnchorAweigh.Button_RescueSOS.Popup_RescueSOS.Button_Chapter03.State_SignalFound",
        )
        return self.window.compare_with_pixel(points_to_check, threshold=1)

    @staticmethod
    def goto_scene_chapter03(window: AzurLaneWindow):
        window.left_click(am.rect("AnchorAweigh.Button_RescueSOS.Popup_RescueSOS.Button_Chapter03"), sleep=1.5)


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

    def __init__(self, window: AzurLaneWindow, scene_from=None):
        super().__init__(window, scene_from)
        self.chapter_no = None

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_main: goto_scene_main,
            Namespace.scene_anchor_aweigh: goto_scene_main,
            Namespace.popup_stage_info: self.open_stage_popup
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "CampaignChapter.Label_WeighAnchor",
            "Main.Icon_Resources.Icon_Oil",
            "Main.Icon_Resources.Icon_Money",
            "Main.Icon_Resources.Icon_Diamond",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    def recognize_chapter_title(self, max_retry=20) -> Union[int, None]:
        chapter_title = self._recognize_chapter_title(self.window, max_retry)
        self.chapter_no = None or self.map_chapter_names.get(chapter_title)
        return self.chapter_no

    @classmethod
    def _recognize_chapter_title(cls, window: AzurLaneWindow, max_retry=20) -> Union[int, None]:
        try:
            x, y, w, h = am.get_image_xywh("CampaignChapter.Chapters.ChapterNo")
            image_processed = slice_image(binarize(window.screenshot(x, y, w, h), thresh=128))

            ocr_paddle.set_valid_chars(cls.unique_chars)
            ocr_text = ocr_paddle(cv2.cvtColor(image_processed, cv2.COLOR_GRAY2RGB))[0][0]
            res = find_most_match(ocr_text, cls.map_chapter_names.keys())[0]

        except:
            res = None
            for _ in range(max_retry):
                if res := cls._recognize_chapter_title(window, max_retry=0) is not None:
                    break

        finally:
            return res

    @staticmethod
    def open_stage_popup(window, chapter_no=None) -> bool:
        window.left_click(am.rect(f"CampaignChapter.Chapters.Stages.{chapter_no}"))

    @staticmethod
    def go_back_to_anchor_aweigh(window) -> bool:
        window.left_click(am.rect("CampaignChapter.Chapters.Button_BackToAnchorAweigh"))
        return False


class PopupStageInfo(Scene):
    name = Namespace.popup_stage_info

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_campaign: self.close_popup,
            Namespace.popup_fleet_selection: self.goto_immediate_start,
            Namespace.popup_fleet_selection_arbitrate: self.goto_immediate_start,
            Namespace.popup_fleet_selection_fixed: self.goto_immediate_start,
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "PopupStageInfo.Label_WeighAnchor",
            "PopupStageInfo.Button_ImmediateStart",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @staticmethod
    def goto_immediate_start(window: AzurLaneWindow):
        window.left_click(am.rect("PopupStageInfo.Button_ImmediateStart"), sleep=1)

    @staticmethod
    def close_popup(window: AzurLaneWindow):
        window.left_click(am.rect("PopupStageInfo.Button_Close"), sleep=1)

    def is_automation(self) -> bool:
        lt, rb = am.rect("PopupStageInfo.Button_Automation")
        mid = tuple(int((lt[i] + rb[i]) / 2) for i in range(2))
        rgb_tuple = self.window.pixel_from_window(*mid, as_int=False)

        return rgb_tuple[0] > 100

    def set_automation(self, turn_on=True, sleep=1):
        if turn_on is not self.is_automation():
            self.window.left_click(am.rect("PopupStageInfo.Button_Automation"), sleep=1)
        time.sleep(sleep)


class PopupFleetSelection(Scene):
    name = Namespace.popup_fleet_selection

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_fleet_fixed = None

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_campaign_chapter: self.close,
            Namespace.scene_campaign: self.goto_immediate_start,
            Namespace.popup_fleet_selection_duty: self.goto_fleet_duty,
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "PopupFleetSelect.Label_FleetSelect",
            "PopupFleetSelect.Label_Marine",
        )
        return window.compare_with_pixel(points_to_check, threshold=1, debug=False)

    @staticmethod
    def goto_immediate_start(window: AzurLaneWindow):
        window.left_click(am.rect("PopupFleetSelect.Button_ImmediateStart"), sleep=1)

    @staticmethod
    def goto_fleet_duty(window: AzurLaneWindow):
        window.left_click(am.rect("PopupFleetSelect.Button_ChangeDuty"), sleep=1)

    @staticmethod
    def close(window: AzurLaneWindow):
        window.left_click(am.rect("PopupFleetSelect.Button_Close"), sleep=1)

    @classmethod
    def _is_fixed_fleet(cls, window: AzurLaneWindow):
        points_to_check = am.eigens(
            "PopupFleetSelect.Button_ChangeFormation",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)


class PopupFleetSelectionArbitrate(PopupFleetSelection):
    name = Namespace.popup_fleet_selection_arbitrate
    map_fleet_no = dict(
        enumerate((f"Button_Fleet{x}" for x in ("One", "Two", "Three", "Four", "Five", "Six")), start=1)
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_fleet_fixed = False

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        return (not cls._is_fixed_fleet(window)) and super().at_this_scene(window)

    @Scene.bind_window
    def choose_team(self, window, team_one=None, team_two=None):
        btns = am.ASSETS["PopupFleetSelect"]["Formation"]

        if (key := self.map_fleet_no.get(team_one)) is not None:
            btn = btns["Button_ChooseTeamOne"]
            window.left_click(btn, sleep=.5)
            window.left_click(btn[key], sleep=.5)

        if (key := self.map_fleet_no.get(team_two)) is not None:
            btn = btns["Button_ChooseTeamTwo"]
            window.left_click(btn, sleep=.5)
            window.left_click(btn[key], sleep=1)


class PopupFleetSelectionFixed(PopupFleetSelection):
    name = Namespace.popup_fleet_selection_fixed

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_fleet_fixed = True

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        return cls._is_fixed_fleet(window) and super().at_this_scene(window)


class PopupFleetSelectionDuty(PopupFleetSelection):
    name = Namespace.popup_fleet_selection_duty

    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_campaign_chapter: self.close,
            Namespace.scene_campaign: self.goto_immediate_start,
            Namespace.popup_fleet_selection_duty: self.goto_fleet_duty,
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        duties = cls.show_duty(window)

        return duties != 0b0 and super().at_this_scene(window)

    @staticmethod
    def show_duty(window):
        btn = "PopupFleetSelect.Button_ChangeDuty"
        cmp = lambda x: window.compare_with_pixel(am.eigens(x), threshold=1)
        res = 0b0

        s0, s1 = (cmp(f"{btn}.Submarine.{state}") for state in ("Button_AutoEngage", "Button_StandBy"))
        if s0 and (not s1):
            res |= 0b1
        elif (not s0) and s1:
            res |= (0b1 << 1)

        for idx, state in enumerate(("Button_StandBy", "Button_AllBattle", "Button_Flagship", "Button_NormalBattle"),
                                    start=2):
            if cmp(f"{btn}.NormalFleet.{state}") is True:
                res |= (0b1 << idx)

        return res

    def set_duty_marine(self, team_one) -> bool:
        btn_marine = am.resolve("PopupFleetSelect.Button_ChangeDuty.NormalFleet")
        duty_marines = {
            0b1000: btn_marine["Button_NormalBattle"],
            0b0100: btn_marine["Button_Flagship"],
            0b0010: btn_marine["Button_AllBattle"],
            0b0001: btn_marine["Button_StandBy"],
        }
        if (duty_marine := duty_marines.get(team_one)) is None:
            return False
        self.window.left_click(duty_marine, sleep=.75)
        return (self.show_duty(self.window) >> 2) == team_one

    def set_duty_submarine(self, team_submarine=0b01) -> bool:
        btn_submarine = am.resolve("PopupFleetSelect.Button_ChangeDuty.Submarine")
        duty_submarines = {
            0b10: btn_submarine["Button_AutoEngage"],
            0b01: btn_submarine["Button_StandBy"],
        }
        if (duty_submarine := duty_submarines.get(team_submarine)) is None:
            return False
        self.window.left_click(duty_submarine, sleep=.75)
        return (self.show_duty(self.window) & 0b000011) == duty_submarine


class SceneCampaignChapter03(SceneCampaignChapter):
    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        return super().at_this_scene(window) and cls._recognize_chapter_title(window) == 3

    def goto_sos_rescue(self, chapter_no=None) -> bool:
        pass


class SceneCampaign(Scene):
    name = Namespace.scene_campaign

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_main: goto_scene_main
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "Campaign.Label_LimitTime",
            "Main.Icon_Resources.Icon_Oil",
            "Main.Icon_Resources.Icon_Money",
            "Main.Icon_Resources.Icon_Diamond",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    def is_automation_on(self) -> bool:
        button = "Campaign.Button_Automation"
        return self.window.compare_with_template(am.rect(button), am.template(f"{button}.State_On"), threshold=.999)

    def is_automation_off(self) -> bool:
        button = "Campaign.Button_Automation"
        return self.window.compare_with_template(am.rect(button), am.template(f"{button}.State_Off"), threshold=.999)

    def is_formation_locked(self):
        points_to_check = am.eigens("Campaign.Button_FormationLock.State_On")
        return self.window.compare_with_pixel(points_to_check, threshold=1)

    def is_strategy_popup(self):
        points_to_check = am.eigens(
            "Campaign.Button_Strategy.State_Expanded"
        )
        return self.window.compare_with_pixel(points_to_check, threshold=1)

    def recognize_fleet_no(self, max_retry=20) -> int:
        x, y, w, h = am.get_image_xywh("Campaign.Label_FleetNo")
        image = self.window.screenshot(x, y, w, h)
        try:
            return int(ocr_int(ocr_preprocess(image), config="--psm 8 --oem 3 -c tessedit_char_whitelist=1234").strip())
        except:
            for _ in range(max_retry):
                res = self.recognize_fleet_no(max_retry=0)
        return res

    def get_fleet_formation(self) -> Optional[str]:
        if self.is_strategy_popup():
            for state in ("State_SingleLineAssault", "State_DoubleLineAdvance", "State_CircularDefense"):
                points_to_check = am.eigens(
                    f"Campaign.Button_Strategy.State_Expanded.Button_SwitchFormation.{state}"
                )
                if self.window.compare_with_pixel(points_to_check, threshold=1):
                    return state
        return None

    @staticmethod
    def _detect_enemy(img_screen, templates, threshold=.1, method=TM_SQDIFF_NORMED):
        res = []
        for img_template in templates:
            res.extend(list(match_multi_template(img_screen, img_template, thresh=threshold, method=method)))

        if len(res) > 0:
            res = combine_similar_points(np.array(res))

        return res

    def detect_enemy(self, scale, img_screen=None, threshold=.1, method=TM_SQDIFF_NORMED):
        if img_screen is None:
            img_screen = self.window.screenshot()

        templates = [am.template(x) for x in am.resolve(f"Campaign.Enemy.Scale.{scale}", "Images").values()]
        res = self._detect_enemy(img_screen, templates, threshold, method)
        if len(res) > 0 and scale != "Boss":
            res += np.array([50, 80])
        else:
            if len(res) == 1:
                res += np.array([30, 30])
        return list(res)

    def attack_enemies(self):
        img_screen_1 = self.window.screenshot()
        time.sleep(1.5)
        img_screen_2 = self.window.screenshot()
        enemy_type = {4: "Boss", 3: "Large", 2: "Medium", 1: "Small"}
        enemies = {
            k: self.detect_enemy(v, img_screen_1)
            for k, v in enemy_type.items()
        }
        for k, v in enemy_type.items():
            enemies[k].extend(self.detect_enemy(v, img_screen_2))
            if len(enemies[k]) > 0:
                enemies[k] = combine_similar_points(np.array(enemies[k]))
        print(enemies)
        for k in (4, 3, 2, 1):
            if len(enemies_found := enemies[k]) > 0:
                self.window.left_click(tuple(enemies_found[0]), sleep=1)
                return True
        return False


class PopupGetShip(Scene):
    name = Namespace.popup_get_ship

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_campaign: self.goto_campaign
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "Campaign.Popup_GetShip",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @staticmethod
    def goto_campaign(window):
        window.left_click(am.rect("Campaign.Popup_GetShip.Button_Exit"), sleep=2)


class PopupCampaignInfo(Scene):
    name = Namespace.popup_campaign_info

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_campaign: self.goto_campaign
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "Campaign.Popup_Information",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @staticmethod
    def goto_campaign(window):
        window.left_click(am.rect("Campaign.Popup_Information.Button_Exit"), sleep=.75)


class PopupInfoAutoBattle(Scene):
    name = Namespace.popup_info_auto_battle

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_battle_formation: self.go_back
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "Popup_Information.AutoBattle",
            "Popup_Information.AutoBattle.Button_Ensure",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @staticmethod
    def go_back(window):
        window.left_click(am.rect("Popup_Information.AutoBattle.Button_Ensure"), sleep=.75)


class SceneBattleFormation(Scene):
    name = Namespace.scene_battle_formation

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_main: goto_scene_main,
            Namespace.scene_battle: self.goto_battle,
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "BeforeBattle.Formation.Button_WeighAnchor",
            "BeforeBattle.Formation.Label_MainFleet",
            "BeforeBattle.Formation.Label_VanguardFleet",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)

    @staticmethod
    def goto_battle(window: AzurLaneWindow):
        window.left_click(am.rect("BeforeBattle.Formation.Button_WeighAnchor"), sleep=2.5)

    def is_automation(self) -> bool:
        points_to_check = am.eigens(
            "BeforeBattle.Formation.Automation.Button_Automation.State_On"
        )
        return self.window.compare_with_pixel(points_to_check, threshold=1)

    def set_automation(self, turn_on=True):
        if self.is_automation() is not turn_on:
            self.window.left_click(am.rect("BeforeBattle.Formation.Automation.Button_Automation"), sleep=1)
        return self.is_automation() is turn_on

    def is_auto_submarine_off(self) -> bool:
        points_to_check = am.eigens(
            "BeforeBattle.Formation.Automation.Button_AutoSubmarine.State_Off"
        )
        return self.window.compare_with_pixel(points_to_check, threshold=1)

    def set_auto_submarine(self, turn_on=False):
        if not self.is_automation():
            return turn_on is False

        if self.is_auto_submarine_off() is turn_on:
            self.window.left_click(am.rect("BeforeBattle.Formation.Automation.Button_AutoSubmarine"), sleep=1)
        return self.is_auto_submarine_off() is turn_on


class SceneBattle(Scene):
    name = Namespace.scene_battle

    @property
    def bounds(self) -> dict:
        destinations = {
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "Battle.Button_Pause",
        )
        return window.compare_with_pixel(points_to_check, threshold=1)


class SceneBattleCheckpoint00(Scene):
    name = Namespace.scene_battle_checkpoint_00

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_campaign: self.quit_scene
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "AfterBattle.Checkpoint_00.Label_Perfect",
        )
        return window.compare_with_pixel(points_to_check)

    @staticmethod
    def quit_scene(window: AzurLaneWindow):
        window.left_click(am.rect("AfterBattle.Checkpoint_00.Button_EmptySpace"), sleep=.75)


class SceneBattleCheckpoint01(Scene):
    name = Namespace.scene_battle_checkpoint_01

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_get_items: self.goto_get_items
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "AfterBattle.Checkpoint_01.Label_Checkpoint",
        )
        return window.compare_with_pixel(points_to_check)

    @staticmethod
    def goto_get_items(window: AzurLaneWindow):
        window.left_click((1850, 200), sleep=.5)


class SceneGetItems(Scene):
    name = Namespace.scene_get_items

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_battle_result: self.goto_battle_results
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check1 = am.eigens(
            "Popup_GetItems.Label_GetItems1",
        )

        points_to_check2 = am.eigens(
            "Popup_GetItems.Label_GetItems2",
        )

        return window.compare_with_pixel(points_to_check1) or window.compare_with_pixel(points_to_check2)

    @staticmethod
    def goto_battle_results(window: AzurLaneWindow):
        window.left_click((1850, 200), sleep=.5)


class SceneBattleResult(Scene):
    name = Namespace.scene_battle_result

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_campaign: self.goto_campaign,
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "AfterBattle.BattleResult.Button_DamageReport",
            "AfterBattle.BattleResult.Button_Ensure",
        )

        return window.compare_with_pixel(points_to_check)

    @staticmethod
    def goto_campaign(window: AzurLaneWindow):
        window.left_click(am.rect("AfterBattle.BattleResult.Button_Ensure"))


class PopupCampaignReward(Scene):
    name = Namespace.popup_campaign_reward

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_campaign: self.goto_campaign
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "CampaignChapter.Label_TotalRewards_without_META",
            "CampaignChapter.Label_TotalRewards_without_META.Button_GoAgain",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @staticmethod
    def goto_campaign(window: AzurLaneWindow):
        window.left_click((1460, 115), sleep=1.5)  # just a random empty space


class PopupCampaignRewardWithMeta(Scene):
    name = Namespace.popup_campaign_reward_meta

    @property
    def bounds(self) -> dict:
        destinations = {
            Namespace.scene_campaign: self.goto_campaign
        }
        return destinations

    @classmethod
    def at_this_scene(cls, window: AzurLaneWindow) -> bool:
        points_to_check = am.eigens(
            "CampaignChapter.Label_TotalRewards_with_META",
            "CampaignChapter.Label_TotalRewards_with_META.Button_GoAgain",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @staticmethod
    def goto_campaign(window: AzurLaneWindow):
        window.left_click((1850, 300), sleep=1.5)  # just a random empty space


scene_names = {
    Namespace.popup_commission: PopupCommission,
    Namespace.scene_delegation_list: SceneDelegationList,

    Namespace.scene_main: SceneMain,
    Namespace.scene_delegation_success: PopupDelegationSuccess,

    Namespace.scene_anchor_aweigh: SceneAnchorAweigh,
    Namespace.popup_rescue_sos: PopupRescueSOS,

    Namespace.scene_campaign: SceneCampaign,
    Namespace.scene_campaign_chapter: SceneCampaignChapter,
    Namespace.popup_stage_info: PopupStageInfo,
    Namespace.popup_fleet_selection: PopupFleetSelection,
    Namespace.popup_fleet_selection_arbitrate: PopupFleetSelectionArbitrate,
    Namespace.popup_fleet_selection_fixed: PopupFleetSelectionFixed,
    Namespace.popup_fleet_selection_duty: PopupFleetSelectionDuty,
    Namespace.popup_campaign_reward: PopupCampaignReward,
    Namespace.popup_campaign_reward_meta: PopupCampaignRewardWithMeta,

    Namespace.scene_battle: SceneBattle,
    Namespace.popup_get_ship: PopupGetShip,
    Namespace.scene_battle_checkpoint_00: SceneBattleCheckpoint00,
    Namespace.scene_battle_checkpoint_01: SceneBattleCheckpoint01,
    Namespace.scene_get_items: SceneGetItems,
    Namespace.scene_battle_result: SceneBattleResult,
    Namespace.popup_info_auto_battle: PopupInfoAutoBattle,
    Namespace.scene_battle_formation: SceneBattleFormation,
}

scenes_registered = [
    PopupCommission,
    SceneDelegationList,

    SceneMain,
    SceneAnchorAweigh,
    PopupDelegationSuccess,

    SceneCampaign,
    PopupGetShip,
    PopupCampaignInfo,
    SceneCampaignChapter,

    PopupStageInfo,
    PopupFleetSelectionDuty, PopupFleetSelectionFixed, PopupFleetSelectionArbitrate, PopupFleetSelection,

    PopupCampaignReward,
    PopupCampaignRewardWithMeta,

    SceneBattle,
    SceneBattleFormation,
    SceneBattleCheckpoint00,
    SceneBattleCheckpoint01,
    SceneGetItems,
    SceneBattleResult,

    PopupRescueSOS,
    PopupInfoAutoBattle,
]
