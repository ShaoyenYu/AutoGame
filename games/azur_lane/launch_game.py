from script import boot


def launch():
    window_name = "BS_AzurLane"
    launch_cmd = "HD-Player.exe --instance Rvc64 --cmd launchApp --package \"com.hkmanjuu.azurlane.gp\""

    simulator = boot.launch(window_name, launch_cmd)
    return simulator
