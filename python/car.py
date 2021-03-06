import time
import threading
from typing import List, Tuple
from enum import Enum, IntEnum


class Command(Enum):
    MAINTAIN_SPEED = '0'
    ACCELERATE = '1'
    BRAKE = '2'
    CHANGE_LANE = '3'
    TERMINATE = '4'


class AccelerationState(Enum):
    MAINTAINING_SPEED = 0
    ACCELERATING = 1
    BRAKING = 2


class Lane(IntEnum):
    MERGE_LANE = 0
    MERGE_TO_TRAFFIC = 1
    TRAFFIC_LANE = 2
    TRAFFIC_TO_EXPRESS = 3
    EXPRESS_TO_TRAFFIC = 4
    EXPRESS_LANE = 5


effective_lanes = [Lane.MERGE_LANE,
                   Lane.TRAFFIC_LANE,
                   Lane.TRAFFIC_LANE,
                   Lane.EXPRESS_LANE,
                   Lane.TRAFFIC_LANE,
                   Lane.EXPRESS_LANE]


class CarSpecs:
    def __init__(self, specs: Tuple[float, float, float, float, float]):
        """
        :param specs[0]: preferred speed [m/sg
        :param specs[1]: max speed [m/s]
        :param specs[2]: acceleration [m/s^2]
        :param specs[3]: braking power [m/s^2]
        :param specs[4]: size of car [m] above 7.5 meter we are talking about a truck
        """
        self.preferred_speed: float = specs[0]
        self.max_speed: float = specs[1]
        self.acceleration: float = specs[2]
        self.braking_power: float = specs[3]
        self.size: float = specs[4]

    def __str__(self):
        return f"<CarSpecs - preferred_speed: {self.preferred_speed}, max_speed: {self.max_speed}, " \
               f"acceleration: {self.acceleration}, braking_power: {self.braking_power}, size: {self.size}>"

    def __repr__(self):
        return self.__str__()


class Car:
    def __init__(self, car_id: str, specs: CarSpecs, state: Tuple[int, float, float, int]):
        """
        see: htcs-vehicle/src/state.h
        :param state[0]: 0 or 1 or 2 or 3 or 4 or 5
        :param state[1]: distance taken along the single axis
        :param state[2]: speed [m/s]
        :param state[3]: enum
        :param specs: constant parameters of the car
        """
        self.id: str = car_id
        self.specs: CarSpecs = specs
        self.lane: Lane = Lane(state[0])
        self.distance_taken: float = state[1]
        self.speed: float = state[2]
        self.acceleration_state: AccelerationState = AccelerationState(state[3])
        self.last_command: Command or None = None
        self.lane_when_last_command: Lane = self.lane
        self.last_state_update: float = time.time()

    def __str__(self):
        return f"<Car - id: {self.id}, lane: {self.lane}, " \
               f"distance_taken: {self.distance_taken}, speed: {self.speed}, " \
               f"acceleration_state: {self.acceleration_state}, specs: {self.specs}>"

    def __repr__(self):
        return self.__str__()

    def update_state(self, state):
        self.lane = Lane(state[0])
        self.distance_taken = state[1]
        self.speed = state[2]
        self.acceleration_state = state[3]
        self.last_state_update: float = time.time()

    def signed_distance_between(self, other_car):
        if other_car is None:
            return float('nan')
        return other_car.distance_taken - self.distance_taken

    def distance_between(self, other_car):
        return abs(self.distance_taken - other_car.distance_taken)

    def follow_distance(self, safety_factor=1.0):
        """
        Distance traveled while getting to a full stop from current speed
        :param safety_factor: returned value will be multiplied by this factor
        """
        # time to stop = speed / deceleration
        # distance traveled = area under the function of speed(time)
        # which is a line from current speed at zero time, and zero speed at time to stop
        follow_distance = (self.speed / 2.0) * (self.speed / self.specs.braking_power)
        return safety_factor * follow_distance

    def distance_while_reaching_speed(self, target_speed):
        """
        Distance traveled while reaching target_speed from current_speed
        """
        # we calculate the area under the function of speed(time) which is a trapezoid
        if self.speed < target_speed:
            return (target_speed + self.speed) / 2 * (target_speed - self.speed) / self.specs.acceleration
        else:
            return (target_speed + self.speed) / 2 * (self.speed - target_speed) / self.specs.braking_power

    def time_to_speed(self, target_speed):
        """
        Time it takes to reach target_speed
        """
        if self.speed < target_speed:
            return target_speed - self.speed / self.specs.acceleration
        else:
            return self.speed - target_speed / self.specs.braking_power

    def match_speed_distance_change(self, other_car, safety_factor=1.0):
        """
        Calculates how much closer the car gets to another car, while getting to the other car's speed
        """
        self_distance_traveled = self.distance_while_reaching_speed(other_car.speed)
        other_car_distance_traveled = self.time_to_speed(other_car.speed) * other_car.speed
        return safety_factor*(self_distance_traveled - other_car_distance_traveled)

    def effective_lane(self):
        return effective_lanes[self.lane.value]


# These classes simulate a dictionary
class CarManager:
    def __init__(self):
        self.as_dict = {}
        self.lock = threading.Lock()

    def __setitem__(self, key, value: Car):
        self.as_dict[key] = value

    def __getitem__(self, key):
        return self.as_dict[key]

    def pop(self, key, default_value=None):
        return self.as_dict.pop(key, default_value)

    def get(self, key):
        return self.as_dict.get(key)

    def values(self):
        return self.as_dict.values()

    def update_car(self, car_id, state):
        self.as_dict[car_id].update_state(state)

    def get_all(self) -> List[Car]:
        # this is a new list of object pointers
        with self.lock:
            return [car for car in self.as_dict.values()]


class DetailedCarTracker(CarManager):
    def __init__(self):
        super().__init__()
        self.full_list: List[Car] = []

    def __getitem__(self, key):
        for car in self.full_list:
            if car.id == key:
                return car
        raise KeyError

    def get(self, key):
        for car in self.full_list:
            if car.id == key:
                return car
        return None

    def __setitem__(self, key, value: Car):
        self.put_into_full_list(value)

    def put_into_full_list(self, value: Car):
        for index_with_bigger_dist in range(0, len(self.full_list)):
            if self.full_list[index_with_bigger_dist].distance_taken > value.distance_taken:
                self.full_list.insert(index_with_bigger_dist, value)
                return
        self.full_list.append(value)

    def update_car(self, car_id, state):
        car = self[car_id]
        car.update_state(state)
        index_now = self.full_list.index(car)
        if index_now < len(self.full_list) - 1 and self.full_list[index_now + 1].distance_taken < car.distance_taken:
            with self.lock:
                self.full_list[index_now], self.full_list[index_now + 1] = \
                    self.full_list[index_now + 1], self.full_list[index_now]
        # we do not have to check the other swap, since the car could not have moved backwards

    def pop(self, key, default_value=None):
        for i in range(0, len(self.full_list)):
            if self.full_list[i].id == key:
                return self.full_list.pop(i)
        return default_value

    def get_all(self) -> List[Car]:
        # this is a new list of object pointers
        with self.lock:
            return [car for car in self.full_list]

    def car_directly_behind_in_effective_lane(self, car_in_focus: Car, lane: Lane):
        try:
            index = self.full_list.index(car_in_focus) - 1
        except ValueError:
            return None
        while index >= 0:
            if self.full_list[index].effective_lane() == lane:
                return self.full_list[index]
            index -= 1
        return None

    def car_directly_ahead_in_effective_lane(self, car_in_focus: Car, lane: Lane):
        try:
            index = self.full_list.index(car_in_focus) + 1
        except ValueError:
            return None
        while index < len(self.full_list):
            if self.full_list[index].effective_lane() == lane:
                return self.full_list[index]
            index += 1
        return None

    def can_overtake(self, car_in_focus: Car):
        if car_in_focus.lane != Lane.TRAFFIC_LANE:
            return False
        car_ahead_if_overtake = self.car_directly_ahead_in_effective_lane(car_in_focus, Lane.EXPRESS_LANE)
        # if road ahead in express lane is not clear
        if car_ahead_if_overtake is not None:
            # if there is a faster vehicle there, we only check not to hit it immediately
            if car_ahead_if_overtake.speed > car_in_focus.speed:
                if car_ahead_if_overtake.distance_taken - car_ahead_if_overtake.specs.size < car_in_focus.distance_taken:
                    return False
            # else we check if we can brake while overtaking and not hit that
            elif car_in_focus.match_speed_distance_change(car_ahead_if_overtake, safety_factor=2.0) > \
                car_in_focus.distance_between(car_ahead_if_overtake):
                return False
        car_behind_if_overtake = self.car_directly_behind_in_effective_lane(car_in_focus, Lane.EXPRESS_LANE)
        # if we cut someone's path
        if car_behind_if_overtake is not None \
                and car_behind_if_overtake.speed > car_in_focus.speed \
                and car_behind_if_overtake.match_speed_distance_change(car_in_focus, safety_factor=2.0) > \
                car_behind_if_overtake.distance_between(car_in_focus):
            return False
        return True

    def can_merge_in(self, car_in_focus: Car):
        if car_in_focus.lane != Lane.MERGE_LANE:
            return False
        if car_in_focus.speed < car_in_focus.specs.preferred_speed * 0.7:
            return False
        car_ahead_if_merge_in = self.car_directly_ahead_in_effective_lane(car_in_focus, Lane.TRAFFIC_LANE)
        # if road ahead in express lane is not clear
        if car_ahead_if_merge_in is not None:
            # if there is a faster vehicle there, we only check not to hit it immediately
            if car_ahead_if_merge_in.speed > car_in_focus.speed:
                if car_ahead_if_merge_in.distance_taken - car_ahead_if_merge_in.specs.size < car_in_focus.distance_taken:
                    return False
            # else we check if we can brake while merging in
            else:
                if car_in_focus.match_speed_distance_change(car_ahead_if_merge_in, safety_factor=2.0) > \
                   car_ahead_if_merge_in.distance_taken - car_in_focus.distance_taken:
                    return False
        car_behind_if_merge_in = self.car_directly_behind_in_effective_lane(car_in_focus, Lane.TRAFFIC_LANE)
        # if we cut someone's path
        if car_behind_if_merge_in is not None \
                and car_behind_if_merge_in.speed > car_in_focus.speed \
                and car_behind_if_merge_in.match_speed_distance_change(car_in_focus, safety_factor=2.0) * 2 > \
                car_in_focus.distance_taken - car_behind_if_merge_in.distance_taken:
            return False
        return True

    def can_return_to_traffic_lane(self, car_in_focus: Car):
        if car_in_focus.lane != Lane.EXPRESS_LANE:
            return False
        if car_in_focus.speed < car_in_focus.specs.preferred_speed:
            return False
        car_behind_if_return = self.car_directly_behind_in_effective_lane(car_in_focus, Lane.TRAFFIC_LANE)
        # Have at least 50 meters between us and the car behind us when we change back
        if car_behind_if_return is not None \
                and car_behind_if_return.distance_taken + 50 > car_in_focus.distance_taken:
            return False
        car_ahead_if_return = self.car_directly_ahead_in_effective_lane(car_in_focus, Lane.TRAFFIC_LANE)
        if car_ahead_if_return is not None \
                and car_ahead_if_return.speed < car_in_focus.specs.preferred_speed \
                and car_ahead_if_return.distance_taken - car_in_focus.distance_taken < car_in_focus.follow_distance(safety_factor=1.3):
            return False
        return True
