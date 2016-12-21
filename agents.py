import bge
import mathutils
import bgeutils

import random
import math
import model_display
import json

import particles
import agent_states
import agent_actions


class TestHouse(object):

    def __init__(self, manager, location):

        self.agent_type = "BUILDING"
        self.manager = manager
        self.location = location
        self.box = self.manager.scene.addObject("test_house", self.manager.own, 0)
        self.size = 9
        self.tile_offset = (self.size * 0.5) - 0.5
        self.team = -1
        self.occupied = []
        self.commands = []
        self.ended = False
        self.selected = False
        self.visible = True

        self.set_position()
        self.set_occupied()
        self.manager.agents.append(self)

    def set_position(self):

        self.box.worldPosition = [self.location[0] + self.tile_offset, self.location[1] + self.tile_offset, 0.0]

        ground_hit = bgeutils.ground_ray(self.box)

        if ground_hit:
            z = ground_hit[1].z
        else:
            z = 0.0

        self.box.worldPosition.z = z

    def set_occupied(self):

        x, y = self.location

        for xp in range(self.size):
            for yp in range(self.size):

                set_key = (x + xp, y + yp)
                marker = None

                if self.manager.debug:
                    marker = self.box.scene.addObject("marker", self.box, 0)
                    marker.worldPosition = (x + xp, y + yp, self.box.worldPosition.copy().z + 5.0)

                self.manager.tiles[set_key].occupied = self
                self.occupied.append([set_key, marker])

    def update(self):
        # need to write code to set visible, and set team if occupied, as well as set HP, do damage etc...

        pass

    def process_commands(self):
        # need code for unloading infantry or aiming infantry

        pass


class Agent(object):

    agent_type = "None"
    ended = False
    selected = False
    selection_group = None
    on_screen = False
    stats = None
    visible = True
    toggle_visible = False

    display_object = None
    movement = None
    animation = None
    size = 4
    tile_offset = (size * 0.5) - 0.5

    extra_movement = 0.0
    throttle = 0.0
    throttle_target = 0.0

    moving = False
    off_road = False
    reversing = False

    def __init__(self, manager, location, load_name, team=0):

        self.manager = manager
        self.manager.agents.append(self)
        self.location = location
        self.team = team

        self.occupied = []

        self.state_name = None
        self.state = None

        self.load_name = load_name
        self.box = self.add_box()

        self.hull = None
        self.agent_hook = None

        if self.box:
            self.hull = bgeutils.get_ob("hull", self.box.childrenRecursive)
            self.agent_hook = bgeutils.get_ob("agent_hook", self.box.childrenRecursive)

            self.debug_text = particles.DebugMessage(self.manager, self.hull, self, [1.0, 0.0, 0.0, 1.0])
            self.debug_message = ""

        self.target_tile = None
        self.enemy_target = None
        self.combat_control = None
        self.commands = []
        self.destinations = []

        self.rotation_target = None
        self.stop_movement = False

        self.facing = (0, 1)
        self.old_facing = (0, 1)

        self.dynamic_stats = {}
        self.set_dynamic_stats()
        self.waypoint = 0

        self.set_position()
        self.starting_state()

    def state_machine(self):
        self.state.update()

        next_state = self.state.transition()
        if next_state:
            self.state.end()
            self.state = next_state(self)
            self.state_name = next_state.__name__

    def update(self):
        if not self.ended:
            self.debug_message = self.state.debug_message

            self.process_commands()
            if not self.manager.paused:
                if self.state:
                    self.state_machine()

    def starting_state(self):
        self.state_name = None
        self.state = None

    def add_box(self):
        return None

    def set_visible(self, value):
        self.visible = value

        for ob in self.agent_hook.childrenRecursive:
            ob.visible = value

    def set_position(self):
        self.box.worldPosition = [self.location[0] + self.tile_offset, self.location[1] + self.tile_offset, 0.0]
        self.clear_occupied()
        self.set_occupied()

    def set_occupied(self):

        x, y = self.location

        for xp in range(self.size):
            for yp in range(self.size):

                set_key = (x + xp, y + yp)
                marker = None

                if self.manager.debug:
                    marker = self.box.scene.addObject("marker", self.box, 0)
                    marker.worldPosition = (x + xp, y + yp, self.hull.worldPosition.copy().z + 2.0)

                self.manager.tiles[set_key].occupied = self
                self.occupied.append([set_key, marker])

    def clear_occupied(self):

        for occupied in self.occupied:
            self.manager.tiles[occupied[0]].occupied = None
            if occupied[1]:
                occupied[1].endObject()

        self.occupied = []

    def check_occupied(self, location):

        x, y = location
        occupied = []

        for xp in range(self.size):
            for yp in range(self.size):
                check_key = (x + xp, y + yp)
                check_tile = self.manager.tiles[check_key].occupied

                if check_tile:
                    if check_tile != self:
                        occupied.append(check_tile)

        if occupied:
            return occupied

    def set_targeter(self):
        self.movement = agent_actions.AgentTargeter(self)

    def set_movement(self):
        self.movement = agent_actions.AgentMovement(self)

    def set_waiting(self):
        self.throttle = 0.0
        self.movement = agent_actions.AgentPause(self)

    def process_commands(self):

        for command in self.commands:

            if command.name == "NUMBER_SELECT":
                number = command.target
                additive = command.additive
                bind = command.condition

                if bind:
                    if self.selected:
                        self.selection_group = number
                    else:
                        if self.selection_group == number:
                            self.selection_group = None

                else:
                    if self.selection_group == number:
                        self.selected = True
                    else:
                        if not additive:
                            self.selected = False

            if command.name == "DE_SELECT":
                self.selected = False

            if command.name == "SELECT":
                if command.condition == "AUTO_SELECT":
                    self.selected = True
                else:
                    cam = self.manager.camera.main_camera

                    if cam.pointInsideFrustum(self.box.worldPosition):
                        x_limit, y_limit = command.position
                        screen_location = cam.getScreenPosition(self.box)

                        if x_limit[0] < screen_location[0] < x_limit[1]:
                            if y_limit[0] < screen_location[1] < y_limit[1]:
                                self.selected = True

            if command.name == "MOVEMENT_TARGET":
                self.enemy_target = None
                destination = (int(round(command.position[0])), int(round(command.position[1])))
                if not command.additive:
                    self.destinations = []
                    self.stop_movement = True
                if command.condition == "REVERSE":
                    if not self.reversing:
                        self.throttle = 0.0
                    self.reversing = True
                else:
                    if self.reversing:
                        self.throttle = 0.0
                    self.reversing = False

                self.destinations.append(destination)

            if command.name == "ROTATION_TARGET":
                self.enemy_target = None
                self.destinations = []
                self.stop_movement = True
                target = (int(round(command.position[0])), int(round(command.position[1])))
                self.rotation_target = target

            if command.name == "SET_ENEMY_TARGET":
                self.destinations = []
                self.stop_movement = True
                self.enemy_target = command.target

        self.commands = []

        if self.selected:
            self.debug_text.text_object.color = [0.0, 1.0, 0.0, 1.0]
        else:
            self.debug_text.text_object.color = [1.0, 0.0, 0.0, 1.0]

    def exit_facing(self):

        search_array = [(1, 0), (1, 1), (0, 1), (1, -1), (-1, 0), (-1, 1), (0, -1), (-1, -1)]

        local_y = self.agent_hook.getAxisVect([0.0, 1.0, 0.0])

        best_facing = None
        best_angle = 4.0

        for facing in search_array:
            facing_vector = mathutils.Vector(facing).to_3d()
            angle = local_y.angle(facing_vector)
            if angle < best_angle:
                best_facing = facing
                best_angle = angle

        self.old_facing = self.facing
        self.facing = best_facing

    def get_facing(self):

        search_array = [(1, 0), (1, 1), (0, 1), (1, -1), (-1, 0), (-1, 1), (0, -1), (-1, -1)]
        current_tile = self.location
        choice = search_array[0]
        closest = 10000.0

        for s in search_array:
            neighbor = (current_tile[0] + s[0], current_tile[1] + s[1])
            distance = (mathutils.Vector(self.rotation_target) - mathutils.Vector(neighbor)).length

            if bgeutils.diagonal(s):
                distance += 0.4

            if distance < closest:
                closest = distance
                choice = s

        if self.facing != choice:
            self.facing = choice
            return True

        return False

    def set_dynamic_stats(self):

        self.dynamic_stats = {'handling': 0.5, 'acceleration': 0.5, 'speed': 0.2, "abs_speed": 0.2,
                              'crew': 1.0, 'drive': 1.0, 'ammo_remaining': 0.0, 'stores_remaining': 0.0, 'HP': 0,
                              'shock': 0,
                              'turning_speed': 0.2, 'display_speed': 0.0, 'weapons': None}

    def update_dynamic_stats(self):
        pass


class VehicleAgent(Agent):

    def __init__(self, manager, location, load_name, team):
        super().__init__(manager, location, load_name, team)

        self.agent_type = "VEHICLE"

    def add_box(self):
        box = self.manager.scene.addObject("agent", self.manager.own, 0)
        return box

    def starting_state(self):
        self.state_name = None
        self.state = agent_states.VehicleStartUp(self)

    def load_vehicle(self):

        in_path = bge.logic.expandPath("//vehicles/saved_vehicles.txt")

        with open(in_path, "r") as infile:
            vehicle_dict = json.load(infile)

        if self.load_name in vehicle_dict:
            vehicle = vehicle_dict[self.load_name]
        else:
            vehicle = vehicle_dict["light tank"]

        self.stats = vehicle['stats']

        if self.team == 0:
            cammo = 2
        else:
            cammo = 4

        self.display_object = model_display.VehicleModel(self.hull, self.stats, cammo=cammo)
        self.stats = self.display_object.stats
        self.size = 3 + self.stats['chassis size']
        self.tile_offset = (self.size * 0.5) - 0.5

    def set_dynamic_stats(self):

        self.dynamic_stats = {'handling': 0.0, 'acceleration': 0.0, 'speed': 0.02, "abs_speed": 0.0,
                              'crew': 1.0, 'drive': 1.0, 'ammo_remaining': 0.0, 'stores_remaining': 0.0, 'HP': 0,
                              'shock': 0,
                              'turning_speed': 0.02, 'display_speed': 0.0, 'weapons': None}

        # add more stats here

    def update_dynamic_stats(self):

        if self.toggle_visible:
            self.toggle_visible = not self.toggle_visible
            self.set_visible(self.visible)

        if self.throttle > self.throttle_target:
            acceleration = 0.2
        else:
            acceleration = self.dynamic_stats['acceleration']

        self.throttle = bgeutils.interpolate_float(self.throttle, self.throttle_target, acceleration)

        drive_mod = 1.0

        if self.reversing:
            if self.stats['drive'] == "WHEELED":
                drive_mod = 0.3
            elif self.stats['drive'] == "HALFTRACK":
                drive_mod = 0.6
            else:
                drive_mod = 0.8

        if self.off_road:
            self.dynamic_stats['handling'] = self.stats['off road handling']
            self.dynamic_stats['abs_speed'] = self.stats['off road'] * 0.003  # 0.0046
            self.dynamic_stats['acceleration'] = self.stats['off road handling'] * 0.002
        else:
            self.dynamic_stats['handling'] = self.stats['on road handling']
            self.dynamic_stats['abs_speed'] = self.stats['on road'] * 0.003  # 0.0046
            self.dynamic_stats['acceleration'] = self.stats['on road handling'] * 0.002

        self.dynamic_stats['speed'] = (self.dynamic_stats['abs_speed'] * drive_mod) * self.throttle
        self.dynamic_stats["turning_speed"] = self.dynamic_stats['acceleration'] * 0.8
        self.dynamic_stats['speed'] = self.dynamic_stats['abs_speed'] * self.throttle
        self.dynamic_stats['display_speed'] = self.dynamic_stats['speed'] * 4.0

        if self.reversing:
            self.dynamic_stats['display_speed'] *= -1.0


class Soldier(object):

    def __init__(self, agent, index):

        self.agent = agent
        self.index = index
        self.dead = False
        self.box = self.agent.box.scene.addObject("infantry_dummy", self.agent.box, 0)
        self.box.visible = False
        self.mesh = self.box.scene.addObject("infantry_dummy_mesh", self.box, 0)

        if self.agent.man_type:
            self.mesh_name = self.agent.man_type
        else:
            meshes = ["HRE_RIFLE", "HRE_SMG", "HRE_ANTI_TANK", "HRE_MG"]
            self.mesh_name = random.choice(meshes)

        self.mesh.setParent(self.box)
        self.mesh.worldPosition.z += 2.0

        self.action = None

    def update(self):

        if not self.action:
            self.action = agent_actions.ManAction(self)
        else:
            self.action.update()


class InfantrySquad(Agent):

    def __init__(self, manager, location, load_name, team):
        super().__init__(manager, location, load_name, team)

        self.agent_type = "INFANTRY"

        load_dict = {"officer": [1, 1, "HRE_OFFICER"],
                     "scout": [3, 1, "HRE_SCOUT"],
                     "mg": [6, 1, "HRE_MG"],
                     "anti-tank": [2, 2, "HRE_ANTI_TANK"],
                     "squad": [5, 3, None]}

        load_details = load_dict[load_name]

        self.man_type = load_details[2]
        self.formation = []
        self.wide = load_details[0]
        self.deep = load_details[1]
        self.spacing = 3.0
        self.avoid_radius = 12

        self.size = 4
        self.tile_offset = (self.size * 0.5) - 0.5

        self.flag = self.agent_hook.scene.addObject("infantry_flag", self.agent_hook, 0)
        self.flag.setParent(self.hull)

        self.men = []
        self.add_squad()

    def set_dynamic_stats(self):

        self.dynamic_stats = {'handling': 0.0, 'acceleration': 0.0, 'speed': 0.03, "abs_speed": 0.0,
                              'crew': 1.0, 'drive': 1.0, 'ammo_remaining': 0.0, 'stores_remaining': 0.0, 'HP': 0,
                              'shock': 0,
                              'turning_speed': 0.015, 'display_speed': 0.0, 'weapons': None}

    def add_box(self):
        box = self.manager.scene.addObject("agent", self.manager.own, 0)
        return box

    def starting_state(self):
        self.state_name = None
        self.state = agent_states.InfantryStartup(self)

    def set_occupied(self):
        pass

    def clear_occupied(self):
        pass

    def check_occupied(self, location):

        x, y = location
        occupied = []

        for xp in range(self.size):
            for yp in range(self.size):
                check_key = (x + xp, y + yp)
                check_tile = self.manager.tiles[check_key].occupied

                if check_tile:
                    if check_tile != self:
                        occupied.append(check_tile)

        if occupied:
            return occupied

    def set_visible(self, value):
        self.visible = value

        for man in self.men:
            man.mesh.visible = value

    def set_formation(self):

        spacing = self.spacing
        half = self.spacing * 0.5

        for y in range(self.deep):
            for x in range(self.wide):
                x_loc = (-self.wide * half) + (x * spacing) + half
                y_loc = (-self.deep * half) + (y * spacing) + half

                self.formation.append(mathutils.Vector([x_loc, y_loc]))

    def add_squad(self):

        self.set_formation()

        for i in range(self.wide * self.deep):
            self.men.append(Soldier(self, i))

    def process_squad(self):

        for man in self.men:
            if not man.dead:
                man.update()

    def process_commands(self):

        for command in self.commands:

            if command.name == "NUMBER_SELECT":
                number = command.target
                additive = command.additive
                bind = command.condition

                if bind:
                    if self.selected:
                        self.selection_group = number
                    else:
                        if self.selection_group == number:
                            self.selection_group = None

                else:
                    if self.selection_group == number:
                        self.selected = True
                    else:
                        if not additive:
                            self.selected = False

            if command.name == "DE_SELECT":
                self.selected = False

            if command.name == "SELECT":
                if command.condition == "AUTO_SELECT":
                    self.selected = True
                else:
                    cam = self.manager.camera.main_camera

                    for man in self.men:
                        if cam.pointInsideFrustum(man.box.worldPosition):
                            x_limit, y_limit = command.position
                            screen_location = cam.getScreenPosition(man.box)

                            if x_limit[0] < screen_location[0] < x_limit[1]:
                                if y_limit[0] < screen_location[1] < y_limit[1]:
                                    self.selected = True

            if command.name == "MOVEMENT_TARGET":
                self.enemy_target = None
                destination = (int(round(command.position[0])), int(round(command.position[1])))
                if not command.additive:
                    self.destinations = []
                    self.stop_movement = True
                if command.condition == "REVERSE":
                    if not self.reversing:
                        self.throttle = 0.0
                    self.reversing = True
                else:
                    if self.reversing:
                        self.throttle = 0.0
                    self.reversing = False

                self.destinations.append(destination)

            if command.name == "ROTATION_TARGET":
                self.enemy_target = None
                self.destinations = []
                self.stop_movement = True
                target = (int(round(command.position[0])), int(round(command.position[1])))
                self.rotation_target = target

            if command.name == "SET_ENEMY_TARGET":
                self.destinations = []
                self.stop_movement = True
                self.enemy_target = command.target

        self.commands = []

        if self.selected:
            self.debug_text.text_object.color = [0.0, 1.0, 0.0, 1.0]
        else:
            self.debug_text.text_object.color = [1.0, 0.0, 0.0, 1.0]
