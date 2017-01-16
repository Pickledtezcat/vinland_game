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
import vehicle_stats


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
    screen_position = None
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
    turret_rotation = 0.0

    moving = False
    off_road = False
    reversing = False
    stance = "FLANK"

    def __init__(self, manager, location, load_name, team=0):

        self.manager = manager
        self.manager.agents.append(self)
        self.location = location
        self.team = team

        self.occupied = []
        self.shell = [(0, 0)]

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

    def set_shell(self):

        self.shell = []

        for x in range(self.size + 1):
            for y in range(self.size + 1):

                x_edge = x == 0 or x == self.size
                y_edge = y == 0 or y == self.size

                if x_edge or y_edge:
                    self.shell.append((x, y))

    def set_occupied(self):

        x, y = self.location

        for tile in self.shell:
            xp, yp = tile
            set_key = (x + xp, y + yp)
            marker = None

            if self.manager.debug:
                marker = self.box.scene.addObject("marker", self.box, 0)
                marker.worldPosition = (x + xp, y + yp, 2.0)

            self.manager.tiles[set_key].occupied = self
            self.occupied.append([set_key, marker])

    def clear_occupied(self):

        for occupied in self.occupied:
            self.manager.tiles[occupied[0]].occupied = False
            if occupied[1]:
                occupied[1].endObject()

        self.occupied = []

    def check_occupied(self, location):

        x, y = location
        occupied = []

        for xp in range(self.size + 1):
            for yp in range(self.size + 1):
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
        self.target_tile = None
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

            if command.name == "STANCE_CHANGE":
                self.stance = command.condition
                self.set_formation()

        self.commands = []

        if self.selected:
            self.debug_text.text_object.color = [0.0, 1.0, 0.0, 1.0]
        else:
            self.debug_text.text_object.color = [1.0, 0.0, 0.0, 1.0]

    def set_formation(self):
        pass

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

        self.dynamic_stats = {"handling": 0.5, "acceleration": 0.5, "speed": 0.2, "abs_speed": 0.2,
                              "crew": 1.0, "drive": 1.0, "ammo_remaining": 0.0, "stores_remaining": 0.0, "HP": 0,
                              "shock": 0, "turret_speed": 0.02,
                              "turning_speed": 0.2, "display_speed": 0.0, "weapons": None}

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

        self.stats = vehicle_stats.load_vehicle(self.load_name)

        if self.team == 0:
            cammo = 3
        else:
            cammo = 4

        self.display_object = model_display.VehicleModel(self.hull, self.stats, owner=self, cammo=cammo)
        self.stats = self.display_object.stats
        self.size = 3 + self.stats.chassis_size
        self.tile_offset = (self.size * 0.5) - 0.5

        self.set_shell()

    def set_dynamic_stats(self):

        self.dynamic_stats = {"handling": 0.0, "acceleration": 0.0, "speed": 0.02, "abs_speed": 0.0,
                              "crew": 1.0, "drive": 1.0, "ammo_remaining": 0.0, "stores_remaining": 0.0, "HP": 0,
                              "shock": 0, "turret_speed": 0.01,
                              "turning_speed": 0.02, "display_speed": 0.0, "weapons": None}

        # add more stats here

    def update_dynamic_stats(self):

        if self.toggle_visible:
            self.toggle_visible = not self.toggle_visible
            self.set_visible(self.visible)

        if self.throttle > self.throttle_target:
            acceleration = 0.2
        else:
            acceleration = self.dynamic_stats["acceleration"]

        self.throttle = bgeutils.interpolate_float(self.throttle, self.throttle_target, acceleration)
        drive_mod = 1.0

        if self.reversing:
            if self.stats.drive_type == "WHEELED":
                drive_mod = 0.3
            elif self.stats.drive_type == "HALFTRACK":
                drive_mod = 0.6
            else:
                drive_mod = 0.8

        handling = self.stats.handling
        speed = self.stats.speed

        if self.off_road:
            self.dynamic_stats["handling"] = handling[1]
            self.dynamic_stats["abs_speed"] = speed[1] * 0.003
            self.dynamic_stats["acceleration"] = handling[1] * 0.002
        else:
            self.dynamic_stats["handling"] = handling[0]
            self.dynamic_stats["abs_speed"] = speed[0] * 0.003
            self.dynamic_stats["acceleration"] = handling[0] * 0.002

        self.dynamic_stats["speed"] = (self.dynamic_stats["abs_speed"] * drive_mod) * self.throttle
        self.dynamic_stats["turning_speed"] = self.dynamic_stats["acceleration"] * 0.8
        self.dynamic_stats["display_speed"] = self.dynamic_stats["speed"] * 4.0

        if self.reversing:
            self.dynamic_stats["display_speed"] *= -1.0


class Soldier(object):

    def __init__(self, agent, index):

        self.agent = agent
        self.index = index
        self.dead = False
        self.prone = False
        self.box = self.agent.box.scene.addObject("infantry_dummy", self.agent.box, 0)
        self.box.visible = False
        self.mesh = self.box.scene.addObject("infantry_dummy_mesh", self.box, 0)

        if self.agent.man_type:
            self.mesh_name = self.agent.man_type
        else:
            meshes = ["HRE_RIFLE", "HRE_SMG", "HRE_ANTI_TANK", "HRE_MG"]
            self.mesh_name = random.choice(meshes)


        self.mesh.worldPosition.z += 1.0
        self.mesh.worldPosition.x -= 0.25
        self.mesh.worldPosition.y -= 0.25
        self.mesh.setParent(self.box)

        self.action = None

    def update(self):

        if not self.action:
            if self.agent.agent_type == "ARTILLERY":
                self.action = agent_actions.ArtilleryManAction(self)
            else:
                self.action = agent_actions.ManAction(self)
        else:
            self.action.update()


class Artillery(Agent):

    def __init__(self, manager, location, load_name, team):
        super().__init__(manager, location, load_name, team)

        self.agent_type = "ARTILLERY"
        self.deployed = 0.0
        self.deploy_speed = 0.02

        self.man_type = "HRE_ENGINEER"
        self.formation = []
        self.avoid_radius = 3
        self.prone = False

        self.men = []
        self.add_squad()

    def set_dynamic_stats(self):

        self.dynamic_stats = {"handling": 0.0, "acceleration": 0.0, "speed": 0.01, "abs_speed": 0.01,
                              "crew": 1.0, "drive": "WHEELED", "ammo_remaining": 0.0, "stores_remaining": 0.0, "HP": 0,
                              "shock": 0, "turret_speed": 0.02, "deploy_speed":0.02,
                              "turning_speed": 0.005, "display_speed": 0.005, "weapons": None}

    def update_dynamic_stats(self):

        if self.toggle_visible:
            self.toggle_visible = not self.toggle_visible
            self.set_visible(self.visible)

        if self.movement:
            self.dynamic_stats['display_speed'] = self.dynamic_stats['speed']
        else:
            self.dynamic_stats['display_speed'] = 0.0

    def add_box(self):
        box = self.manager.scene.addObject("agent", self.manager.own, 0)
        return box

    def starting_state(self):
        self.state_name = None
        self.state = agent_states.ArtilleryStartUp(self)

    def load_vehicle(self):

        self.stats = vehicle_stats.load_vehicle(self.load_name)

        if self.team == 0:
            cammo = 2
        else:
            cammo = 4

        self.display_object = model_display.ArtilleryModel(self.hull, self.stats, owner=self, cammo=cammo)
        self.stats = self.display_object.stats
        self.size = 3 + self.stats.chassis_size
        self.tile_offset = (self.size * 0.5) - 0.5

        self.set_shell()

        if self.stats.weight > 12:
            self.dynamic_stats['speed'] = 0.025
            self.dynamic_stats['turning_speed'] = 0.001
            self.dynamic_stats['deploy_speed'] = 0.005

        elif self.stats.weight > 7:
            self.dynamic_stats['speed'] = 0.05
            self.dynamic_stats['turning_speed'] = 0.003
            self.dynamic_stats['deploy_speed'] = 0.01

        elif self.stats.weight > 5:
            self.dynamic_stats['speed'] = 0.1
            self.dynamic_stats['turning_speed'] = 0.005
            self.dynamic_stats['deploy_speed'] = 0.015

        else:
            self.dynamic_stats['speed'] = 0.13
            self.dynamic_stats['turning_speed'] = 0.007
            self.dynamic_stats['deploy_speed'] = 0.02

    def set_visible(self, value):
        self.visible = value

        for man in self.men:
            man.mesh.visible = value

    def set_starting_formation(self):

        self.formation = []
        points = self.display_object.crew_adders

        for point in points:
            position = (point.worldPosition - self.box.worldPosition).to_3d()
            self.formation.append(position)

    def set_formation(self):

        if self.stance == "AGGRESSIVE":
            self.prone = False
            self.dynamic_stats["speed"] = 0.025

        if self.stance == "SENTRY":
            self.prone = False
            self.dynamic_stats["speed"] = 0.02

        if self.stance == "DEFEND":
            self.prone = True
            self.dynamic_stats["speed"] = 0.015

        if self.stance == "FLANK":
            self.prone = False
            self.dynamic_stats["speed"] = 0.03

    def add_squad(self):

        self.set_starting_formation()
        self.set_formation()

        points = self.display_object.crew_adders

        for i in range(len(points)):
            self.men.append(Soldier(self, i))

    def process_squad(self):

        for man in self.men:
            if not man.dead:
                man.update()


class InfantrySquad(Agent):

    def __init__(self, manager, location, load_name, team):
        super().__init__(manager, location, load_name, team)

        self.agent_type = "INFANTRY"

        load_dict = {"officer": [1, 1, "HRE_OFFICER"],
                     "engineer": [2, 1, "HRE_ENGINEER"],
                     "mg": [6, 1, "HRE_MG"],
                     "anti-tank": [2, 2, "HRE_ANTI_TANK"],
                     "squad": [5, 3, None]}

        load_details = load_dict[load_name]

        self.man_type = load_details[2]
        self.formation = []
        self.wide = load_details[0]
        self.deep = load_details[1]
        self.spacing = 3.0
        self.scatter = 0.0
        self.avoid_radius = 12
        self.prone = False

        self.size = 4
        self.tile_offset = (self.size * 0.5) - 0.5

        self.flag = self.agent_hook.scene.addObject("infantry_flag", self.agent_hook, 0)
        self.flag.setParent(self.hull)

        self.men = []
        self.add_squad()

    def set_dynamic_stats(self):

        self.dynamic_stats = {"handling": 0.0, "acceleration": 0.0, "speed": 0.03, "abs_speed": 0.0,
                              "crew": 1.0, "drive": "FOOT", "ammo_remaining": 0.0, "stores_remaining": 0.0, "HP": 0,
                              "shock": 0,
                              "turning_speed": 0.015, "display_speed": 0.0, "weapons": None}

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

        self.formation = []

        order = [self.deep, self.wide]
        spacing = self.spacing * 2.0
        scatter = 0.0
        y_offset = 0.0
        x_offset = 0

        if self.stance == "AGGRESSIVE":
            self.prone = False
            self.avoid_radius = 3
            self.dynamic_stats["speed"] = 0.025
            order = [self.deep, self.wide]
            spacing = self.spacing * 1.5
            scatter = spacing * 0.2

        if self.stance == "SENTRY":
            self.prone = False
            self.avoid_radius = 6
            self.dynamic_stats["speed"] = 0.02
            order = [self.deep, self.wide]
            spacing = self.spacing * 3.0
            scatter = spacing * 0.5

        if self.stance == "DEFEND":
            self.prone = True
            self.avoid_radius = 12
            self.dynamic_stats["speed"] = 0.015
            order = [self.deep, self.wide]
            spacing = self.spacing * 2.0
            scatter = spacing * 0.1

        if self.stance == "FLANK":
            self.prone = False
            self.avoid_radius = 12
            self.dynamic_stats["speed"] = 0.03
            order = [self.wide, self.deep]
            spacing = self.spacing
            scatter = 0.5

        half = spacing * 0.5

        def s_value(scatter_value):
            return scatter_value - (scatter_value * random.uniform(0.0, 2.0))

        for y in range(order[0]):
            for x in range(order[1]):

                if order[0] > 1:
                    y_offset = ((order[0] - 2) * spacing)

                if order[1] % 2 != 0:
                    x_offset = spacing * 0.5

                x_loc = (-self.wide * half) + (x * spacing) + half + s_value(scatter) + x_offset
                y_loc = (-self.deep * half) + (y * spacing) + half + s_value(scatter) - y_offset

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

            if command.name == "STANCE_CHANGE":
                self.stance = command.condition
                self.set_formation()

        self.commands = []

        if self.selected:
            self.debug_text.text_object.color = [0.0, 1.0, 0.0, 1.0]
        else:
            self.debug_text.text_object.color = [1.0, 0.0, 0.0, 1.0]
