from games.azur_lane.interface.scene.asset_manager import am
from games.azur_lane.interface.scene.base import Scene, goto_scene_main
from games.azur_lane.interface.scene.name import Namespace

__all__ = [
    "SceneBattle", "SceneBattleCheckpoint00", "SceneBattleCheckpoint01", "SceneBattleResult",
    "SceneBattleFormation"
]


class SceneBattleFormation(Scene):
    name = Namespace.scene_battle_formation

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "BeforeBattle.Formation.Button_WeighAnchor",
            "BeforeBattle.Formation.Label_MainFleet",
            "BeforeBattle.Formation.Label_VanguardFleet",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_battle(cls, window):
        window.left_click(am.rect("BeforeBattle.Formation.Button_WeighAnchor"), sleep=2.5)

    @classmethod
    def is_automation(cls, window) -> bool:
        points_to_check = am.eigens(
            "BeforeBattle.Formation.Automation.Button_Automation.State_On"
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def set_automation(cls, window, turn_on=True):
        if cls.is_automation(window) is not turn_on:
            window.left_click(am.rect("BeforeBattle.Formation.Automation.Button_Automation"), sleep=1)
        return cls.is_automation(window) is turn_on

    @classmethod
    def is_auto_submarine_off(cls, window) -> bool:
        points_to_check = am.eigens(
            "BeforeBattle.Formation.Automation.Button_AutoSubmarine.State_Off"
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def set_auto_submarine(cls, window, turn_on=False):
        if not cls.is_automation(window):
            return turn_on is False

        if cls.is_auto_submarine_off(window) is turn_on:
            window.left_click(am.rect("BeforeBattle.Formation.Automation.Button_AutoSubmarine"), sleep=1)
        return cls.is_auto_submarine_off(window) is turn_on

    ways = {
        Namespace.scene_main: goto_scene_main,
        Namespace.scene_battle: goto_battle,
    }


class SceneBattle(Scene):
    name = Namespace.scene_battle

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "Battle.Button_Pause",
        )
        return cls.compare_with_pixels(window, points_to_check)


class SceneBattleCheckpoint00(Scene):
    name = Namespace.scene_battle_checkpoint_00

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "AfterBattle.Checkpoint_00.Label_Perfect",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def quit_scene(cls, window):
        window.left_click(am.rect("AfterBattle.Checkpoint_00.Button_EmptySpace"), sleep=.75)

    ways = {
        Namespace.scene_campaign: quit_scene
    }


class SceneBattleCheckpoint01(Scene):
    name = Namespace.scene_battle_checkpoint_01

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "AfterBattle.Checkpoint_01.Label_Checkpoint",
        )
        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_get_items(cls, window):
        window.left_click((1850, 200), sleep=.5)

    ways = {
        Namespace.scene_get_items: goto_get_items
    }


class SceneBattleResult(Scene):
    name = Namespace.scene_battle_result

    @classmethod
    def at_this_scene_impl(cls, window) -> bool:
        points_to_check = am.eigens(
            "AfterBattle.BattleResult.Button_DamageReport",
            "AfterBattle.BattleResult.Button_Ensure",
        )

        return cls.compare_with_pixels(window, points_to_check)

    @classmethod
    def goto_campaign(cls, window):
        window.left_click(am.rect("AfterBattle.BattleResult.Button_Ensure"))

    ways = {
        Namespace.scene_campaign: goto_campaign,
    }
