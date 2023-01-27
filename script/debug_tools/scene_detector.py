import signal
import sys
import time

from games.azur_lane.interface.scene.campaign import SceneCampaignChapter
from games.azur_lane.interface.scene.login import PopupInformationStyle001
from games.azur_lane.manager import SceneManager
from util.window import GameWindow

if __name__ == '__main__':
    window = GameWindow(window_name="BS_AzurLane")
    scene_manager = SceneManager(window)
    scene_manager.logger.setLevel("DEBUG")
    scene_manager.start()


    def close(signum, frame):
        scene_manager.close()
        sys.exit(0)


    signal.signal(signal.SIGINT, close)

    while True:
        if scene_manager.scene_cur.at(PopupInformationStyle001):
            scene_manager.scene_cur.recognize_text(scene_manager.window)
        if scene_manager.scene_cur.at(SceneCampaignChapter):
            text = scene_manager.scene_cur.recognize_chapter_title(scene_manager.window)
            print(text)
        time.sleep(1)
