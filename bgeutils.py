import bge

import random
from mathutils import Vector, Matrix, geometry

import math


class RayHit(object):
    def __init__(self, hit_object, point, normal):
        self.hit_object = hit_object
        self.point = point
        self.normal = normal


class Waypoints(object):
    def __init__(self, manager):
        self.manager = manager

        locations = ([12, 12], [12, 230], [230, 230], [230, 12])
        number = len(locations)

        self.point_list = []

        for i in range(number):
            waypoint = locations[i]

            previous = i - 1

            if i >= number - 1:
                next_point = 0
            else:
                next_point = i + 1

            neighbor_1 = locations[previous]
            neighbor_2 = locations[next_point]

            self.point_list.append(WayPoint(waypoint, [neighbor_1, neighbor_2]))


class WayPoint(object):
    def __init__(self, location, neighbors):

        self.location = get_key(location)
        self.neighbors = [get_key(neighbor) for neighbor in neighbors]


class AgentCommand(object):
    def __init__(self, name, condition=None, position=None, target=None, additive=False):
        self.name = name
        self.condition = condition
        self.position = position
        self.target = target
        self.additive = additive


def get_key(position):
    return int(round(position[0])), int(round(position[1]))


def get_terrain_position(position):

    x, y = position[0], position[1]

    return int(round(x * 0.125)), int(round(y * 0.125))


def smoothstep(x):
    return x * x * (3 - 2 * x)


def get_ob(string, ob_list):
    ob_list = [ob for ob in ob_list if ob.get(string)]
    if ob_list:
        return ob_list[0]


def get_ob_list(string, ob_list):
    ob_list = [ob for ob in ob_list if string in ob]

    return ob_list


def interpolate_float(current, target, factor):

    return (current * (1.0 - factor)) + (target * factor)


def ground_ray(game_object, survey_point=None):

    if survey_point:
        position = survey_point
    else:
        position = game_object.worldPosition.copy()

    up = position.copy()
    up.z += 1000.0
    down = position.copy()
    down.z -= 1000.0

    hit_object, hit_point, hit_normal = game_object.rayCast(down, up, 0.0, "ground", 1, 1, 0)

    if hit_object:
        return [hit_object, hit_point, hit_normal]

    return None


def add_entry(entry, item_list):
    if entry:
        if entry not in item_list:
            item_list.append(entry)
    return item_list


def diagonal(location):

    x, y = location
    if abs(x) - abs(y) == 0:
        return True


def change_direction(last, current):

    lx, ly = last
    cx, cy = current

    if lx != cx and ly != cy:
        return True


def rand_axis(maximum):
    return maximum - (random.uniform(0, maximum * 2.0))


def rand_axis_high(maximum, height):
    return [rand_axis(maximum), rand_axis(maximum), max(height, (height * random.uniform(0.0, 2.0)))]


def rand_axis_center(maximum):
    return [rand_axis(maximum) for _ in range(3)]
