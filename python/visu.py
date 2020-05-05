import os
import cv2
import ast
import random
import logging
import numpy as np
from HTCSPythonUtil import mqtt_connector, get_connection_config, local_cars, Car, on_connect


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("HTCS_Visualization")
# SOME GLOBAL VARIABLES
CONNECTION_CONFIG = get_connection_config()
# image resources
WINDOW_NAME = "Highway Traffic Control System Visualization"
im_map = cv2.imread(os.path.dirname(os.path.abspath(__file__)) + "/res/map.png")
red_car_straight = cv2.imread(os.path.dirname(os.path.abspath(__file__)) + "/res/car1.png")
red_car_left = cv2.imread(os.path.dirname(os.path.abspath(__file__)) + "/res/car1left.png")
red_car_right = cv2.imread(os.path.dirname(os.path.abspath(__file__)) + "/res/car1right.png")
blue_car_straight = cv2.imread(os.path.dirname(os.path.abspath(__file__)) + "/res/car2.png")
blue_car_left = cv2.imread(os.path.dirname(os.path.abspath(__file__)) + "/res/car2left.png")
blue_car_right = cv2.imread(os.path.dirname(os.path.abspath(__file__)) + "/res/car2right.png")
# for calculations
map_length = im_map.shape[1]
center_fast_lane = 180
center_slow_lane = 300
center_merge_lane = 420
max_car_size_pixel = int(0.86 * (center_slow_lane - center_fast_lane))
# for navigation
current_offset = 0
current_region_width = map_length

commands = dict([(0, "Maintain speed!"), (1, "Accelerate!"), (2, "Brake!"), (3, "Switch lanes!")])
# TODO: error raising does not do anything on that thread
def on_message_vis(mqttc, obj, msg):
    topic_parts = msg.topic.split('/')
    if topic_parts[1] == "vehicles":
        car_id = topic_parts[-2]
        msg_type = topic_parts[-1]
        if msg_type == "join":
            if car_id in local_cars.keys():
                logger.warning(f"Car with already existing id ({car_id}) sent a join message")
            else:
                try:
                    specs = ast.literal_eval("{" + msg.payload.decode("utf-8") + "}")
                    local_cars[car_id] = CarImage(0, 0, specs['size'])
                except TypeError:
                    logger.warning(f"Received a badly formatted join message from id {car_id}: {msg.payload.decode('utf-8')}")
        elif msg_type == "state":
            if car_id not in local_cars.keys():
                logger.warning(f"Car with unrecognized id ({car_id}) sent a state message")
            else:
                try:
                    state = ast.literal_eval("{" + msg.payload.decode("utf-8") + "}")
                    local_cars[car_id].car.update_state(**state)
                except TypeError:
                    logger.warning(f"Received a badly formatted state message from id {car_id}: {msg.payload.decode('utf-8')}")
        elif msg_type == "command":
            if car_id in local_cars.keys():
                logger.info(f"Car with id {car_id} received a command: {commands[int(msg.payload.decode('utf-8'))]}")
            else:
                logger.warning(f"Car with unrecognized id ({car_id}) received a command: {commands[int(msg.payload.decode('utf-8'))]}")
        else:
            logger.warning(f"Unrecognized topic: {msg_type}")


# class for visualization
class CarImage:
    def __init__(self, distance_taken, lane, size):
        # Create Car
        self.car = Car.for_visualization(distance_taken, lane, size)
        # Red or Blue
        if bool(random.getrandbits(1)):
            self.straight = red_car_straight
            self.left = red_car_left
            self.right = red_car_right
        else:
            self.straight = blue_car_straight
            self.left = blue_car_left
            self.right = blue_car_right
        # Scale to correct size
        orig_h, orig_w = self.straight.shape[:2]
        new_h = np.round(max_car_size_pixel * self.car.specs.size / CONNECTION_CONFIG["max_car_size"]).astype(np.int32)
        new_w = np.round(orig_w * new_h / orig_h).astype(np.int32)
        self.straight = cv2.resize(self.straight, (new_w, new_h))
        self.left = cv2.resize(self.left, (new_w, new_h))
        self.right = cv2.resize(self.right, (new_w, new_h))

    def get_y_slice(self):
        if self.car.lane == 0:
            start = int(center_merge_lane - self.straight.shape[0] / 2)
        elif self.car.lane == 1:
            start = int((center_merge_lane + center_slow_lane) / 2 - self.straight.shape[0] / 2)
        elif self.car.lane == 2:
            start = int(center_slow_lane - self.straight.shape[0] / 2)
        elif self.car.lane in [3, 4]:
            start = int((center_slow_lane + center_fast_lane) / 2 - self.straight.shape[0] / 2)
        elif self.car.lane == 5:
            start = int(center_fast_lane - self.straight.shape[0] / 2)
        return slice(start, start + self.straight.shape[0])

    def get_x_slice(self):
        possible_maximum = map_length - self.straight.shape[1]
        start = np.floor(possible_maximum * self.car.get_relative_position(CONNECTION_CONFIG)).astype(np.int32)
        return slice(start, start + self.straight.shape[1])

    def get_image(self):
        if self.car.lane in [0, 2, 5]:
            return self.straight
        elif self.car.lane in [1, 3]:
            return self.left
        elif self.car.lane == 4:
            return self.right


def display_state(cars):
    global current_offset, current_region_width

    vis = im_map.copy()
    for carId, car in cars.items():
        vis[car.get_y_slice(), car.get_x_slice(), :] = car.get_image()

    c = cv2.waitKey(20)
    if c == ord('a'):
        current_offset -= 30
    elif c == ord('d'):
        current_offset += 30
    elif c == ord('w'):
        if current_region_width > map_length * 0.1:
            current_region_width = np.floor(current_region_width * 0.95).astype(np.int32)
            _, _, wW, wH = cv2.getWindowImageRect(WINDOW_NAME)
            cv2.resizeWindow(WINDOW_NAME, wW, int(wH / 0.95))
    elif c == ord('s'):
        new_region_width = np.floor(current_region_width / 0.95).astype(np.int32)
        if new_region_width <= map_length:
            current_region_width = new_region_width
            _, _, window_w, window_h = cv2.getWindowImageRect(WINDOW_NAME)
            cv2.resizeWindow(WINDOW_NAME, window_w, int(window_h * 0.95))
        else:
            current_region_width = map_length
    elif c == ord('x'):
        return False
    current_offset = max(min(current_offset, map_length - current_region_width), 0)

    cv2.imshow(WINDOW_NAME, vis[:, current_offset: current_offset + current_region_width, :])
    return True


if __name__ == "__main__":
    mqtt_connector.username_pw_set(username=CONNECTION_CONFIG["username"], password=CONNECTION_CONFIG["password"])
    mqtt_connector.on_connect = on_connect
    mqtt_connector.on_message = on_message_vis
    mqtt_connector.connect(CONNECTION_CONFIG["address"], 1883, 60)
    mqtt_connector.subscribe(CONNECTION_CONFIG["base_topic"], CONNECTION_CONFIG["quality_of_service"])
    mqtt_connector.loop_start()

    cv2.namedWindow(WINDOW_NAME, flags=cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 1800, 250)

    go_on = True
    while go_on:
        go_on = display_state(local_cars)

    mqtt_connector.loop_stop()

