from script import boot

if __name__ == '__main__':
    window_name = "BS_AzurLane"
    launch_cmd = "HD-Player.exe --instance Rvc64 --cmd launchApp --package \"com.hkmanjuu.azurlane.gp\""

    boot.launch(window_name, launch_cmd)
