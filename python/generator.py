import os
import uuid
import time
import signal
import random
import pathlib
import datetime
import subprocess
from HTCSPythonUtil import CONFIG


repo_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
executable_name_windows = repo_root_dir + "/htcs-vehicle/Debug/htcs-vehicle.exe"
executable_name_linux = repo_root_dir + "/htcs-vehicle/build/htcs_vehicle"
logs_dir = repo_root_dir + "/python/logs"
GENERATE_TIME_INTERVAL_MIN = 4
GENERATE_TIME_INTERVAL_WIDTH = 1
PREF_SPEED_INTERVAL_MIN = 50
PREF_SPEED_INTERVAL_WIDTH = 110
MAX_SPEED_INTERVAL_MIN = 100
MAX_SPEED_INTERVAL_WIDTH = 180
ACCELERATION_INTERVAL_MIN = 3
ACCELERATION_INTERVAL_WIDTH = 11
BRAKING_POWER_INTERVAL_MIN = 3
BRAKING_POWER_INTERVAL_WIDTH = 11
SIZE_INTERVAL_MIN = 3
SIZE_INTERVAL_WIDTH = 3
running_children = []


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True
        for pid in running_children:
            # TODO: WHAT IF THEY ARE ALREADY TERMINATED (maybe nothing)
            pid.terminate()


if __name__ == "__main__":
    if os.name is not 'nt':
        os.putenv("LD_LIBRARY_PATH", os.getenv("HOME") + "/Eclipse-Paho-MQTT-C-1.3.1-Linux/lib")

    killer = GracefulKiller()
    now = datetime.datetime.now()
    now_str = now.strftime('%Y%m%d%H%M%S')
    current_logs_dir = logs_dir + "/generation-" + now_str
    pathlib.Path(current_logs_dir).mkdir(exist_ok=True, parents=True)
    while not killer.kill_now:
        sleep_time = random.random() * GENERATE_TIME_INTERVAL_WIDTH + GENERATE_TIME_INTERVAL_MIN
        client_id = str(uuid.uuid4())
        params_string = f"--address {CONFIG['address']} " \
                        f"--username {CONFIG['username']} " \
                        f"--password {CONFIG['password']} " \
                        f"--clientId {client_id} " \
                        f"--topic {CONFIG['base_topic']} " \
                        f"--preferredSpeed {random.random() * PREF_SPEED_INTERVAL_WIDTH + PREF_SPEED_INTERVAL_MIN} " \
                        f"--maxSpeed {random.random() * MAX_SPEED_INTERVAL_WIDTH + MAX_SPEED_INTERVAL_MIN} " \
                        f"--acceleration {random.random() * ACCELERATION_INTERVAL_WIDTH + ACCELERATION_INTERVAL_MIN} " \
                        f"--brakingPower {random.random() * BRAKING_POWER_INTERVAL_WIDTH + BRAKING_POWER_INTERVAL_MIN} " \
                        f"--size {random.random() * SIZE_INTERVAL_WIDTH + SIZE_INTERVAL_MIN}"

        file_h = open(current_logs_dir + "/htcs_vehicle-" + client_id + ".log", "w")
        if os.name == 'nt':
            running_children.append(subprocess.Popen(f'"{executable_name_windows}" ' + params_string,
                                                     shell=True, stdout=file_h, stderr=file_h))
        else:
            running_children.append(subprocess.Popen(executable=executable_name_linux, args=params_string.split(' '),
                                                     shell=True, stdout=file_h, stderr=file_h))
        time.sleep(sleep_time)
