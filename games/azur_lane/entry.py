from games.azur_lane import logger_azurlane
from util.controller.simulator import Bluestack

if __name__ == '__main__':
    bs = Bluestack("BS_AzurLane")
    bs.gateway.start()
    task_available = {"1": "FarmChapter", "2": "FarmSubmarineSOS", "3": "TaskFarmCampaignSpecial", "4": "TaskAutoLogin"}
    logger_azurlane.info(f"Available tasks: {task_available}")

    while True:
        cmd = input(">>>\n")
        if cmd == "exit":
            bs.gateway.close()
            logger_azurlane.info("Finished.")
            break
        elif cmd == "ls":
            bs.gateway.task_manager.list_task()
        elif len(split_cmd := cmd.split(" ")) == 2:
            action, task_no = split_cmd
            task_name = task_available[task_no]

            if action == "start":
                bs.gateway.task_manager.start_task(task_name)
            elif action == "stop":
                bs.gateway.task_manager.stop_task(task_name)
