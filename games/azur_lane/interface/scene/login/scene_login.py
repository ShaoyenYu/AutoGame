from games.azur_lane.interface.scene.asset_manager import am
from games.azur_lane.interface.scene.base import Scene, ocr_origin
from games.azur_lane.interface.scene.name import Namespace
from util.game_cv import slice_image, binarize, find_most_match

__all__ = [
    "SceneLogin", "SceneLoginByAccount", "SceneLoginByThirdParty", "SceneLoginByGoogle", "PopupInformationStyle001",
]


class SceneLogin(Scene):
    name = Namespace.scene_login

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Login",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def login(cls, window):
        window.left_click(am.rect("Login"), sleep=.75)

    ways = {
        Namespace.scene_main: login,
    }


class SceneLoginByAccount(Scene):
    name = Namespace.scene_login_by_account

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Login.ByAccount",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def login_by_third_party(cls, window):
        window.left_click(am.rect("Login.ByAccount.Button_ByThirdParty"), sleep=.75)

    ways = {
        Namespace.scene_login_by_third_party: login_by_third_party,
    }


class SceneLoginByThirdParty(Scene):
    name = Namespace.scene_login_by_third_party

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Login.ByThirdParty",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def login_by_account(cls, window):
        window.left_click(am.rect("Login.ByThirdParty.Button_ByAccount"), sleep=.75)

    @classmethod
    def login_by_google(cls, window):
        window.left_click(am.rect("Login.ByThirdParty.Button_ByGoogle"), sleep=.75)

    ways = {
        Namespace.scene_login_by_account: login_by_account,
        Namespace.scene_login_by_google: login_by_google,
    }


class SceneLoginByGoogle(Scene):
    name = Namespace.scene_login_by_google

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Login.ByGoogle",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def choose_account(cls, window):
        window.left_click(am.rect("Login.ByGoogle.Account_01"), sleep=.75)

    ways = {
        Namespace.scene_login_by_google: choose_account,
    }


class PopupInformationStyle001(Scene):
    name = Namespace.popup_information_s001

    phrases = {
        "檢測到船塢數據遺失是否重新讀取?": 0,
    }

    @classmethod
    def _unique_chars(cls):
        return "".join(cls.phrases)

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Popups.Information.Style_001",
        )
        points_to_check_false = am.eigens(
            "Popups.Information.Style_002",
        )
        return cls.compare_with_pixels(window, points_to_check) and not cls.compare_with_pixels(window, points_to_check_false)

    @classmethod
    def recognize_text(cls, window) -> int:
        x, y, w, h = am.get_image_xywh("Popups.Information.Style_001")
        screenshot = window.screenshot(x, y, w, h)
        image_processed_grey = slice_image(binarize(screenshot, thresh=190))
        text_ocr = ocr_origin.ocr(image_processed_grey)[0][0][1][0]
        text_matched = find_most_match(text_ocr, cls.phrases.keys())[0]
        return cls.phrases[text_matched]

    @classmethod
    def exit(cls, window):
        window.left_click(am.rect("Popups.Information.Style_001.Button_OK"), sleep=.75)

    ways = {
        Namespace.scene_login_by_account: exit
    }
