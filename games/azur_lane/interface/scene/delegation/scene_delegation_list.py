from games.azur_lane.interface.scene.asset_manager import am
from games.azur_lane.interface.scene.base import Scene, goto_scene_main
from games.azur_lane.interface.scene.name import Namespace

__all__ = ["PopupDelegationSuccess", "SceneDelegationList"]


class PopupDelegationSuccess(Scene):
    name = Namespace.popup_delegation_success

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Main.Button_Commission.Popup_Commission.Popup_DelegationSuccess",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_popup_get_items(cls, window):
        window.left_click(
            am.rect("Main.Button_Commission.Popup_Commission.Delegation.Popup_DelegationSuccess.Button_ExitScene"),
            sleep=1
        )

    ways = {
        Namespace.scene_get_items: goto_popup_get_items,
    }


class SceneDelegationList(Scene):
    name = Namespace.scene_delegation_list

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Scene_DelegationList.Label_Delegation",
            "Scene_DelegationList.Label_AvailableFleets",
        )
        return cls.compare_with_pixels(window, points_to_check)

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

    ways = {
        Namespace.scene_main: goto_scene_main
    }
