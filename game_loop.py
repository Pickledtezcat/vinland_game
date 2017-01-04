import bge
import bgeutils

import random
import math

import mathutils

import game_states
import particles
import agents

import terrain_generation
import LOS

import game_input
import camera_control
import time


class MovementAction(object):
    def __init__(self, manager):
        self.manager = manager
        self.movement_point = None
        self.movement_direction = None
        self.center_point = None
        self.movement_markers = []
        self.rotation_countdown = 15

        if self.manager.context == "TARGET":
            target = self.manager.mouse_over_unit
            selected_agents = [agent for agent in self.manager.agents if agent.selected]
            for agent in selected_agents:
                agent.commands.append(bgeutils.AgentCommand("SET_ENEMY_TARGET", target=target))

        elif self.manager.tile_over:

            self.movement_point = mathutils.Vector(self.manager.tile_over)
            selected_agents = [agent for agent in self.manager.agents if agent.selected]

            center_point = mathutils.Vector().to_2d()

            for selected_agent in selected_agents:
                center_point += selected_agent.box.worldPosition.copy().to_2d()

            if center_point.length:
                center_point /= len(selected_agents)

            self.center_point = center_point

            for selected_agent in selected_agents:
                offset = self.center_point.copy() - selected_agent.box.worldPosition.copy().to_2d()
                target_point = self.movement_point.copy() - offset

                self.movement_markers.append(MovementMarker(self.manager, selected_agent, target_point, offset))

    def update(self):

        if self.rotation_countdown > 0:
            self.rotation_countdown -= 1
        else:
            vector_start = self.movement_point
            ground_hit = self.manager.tiles[bgeutils.get_key(self.manager.tile_over)]

            vector_end = ground_hit.point.to_2d()

            movement_vector = vector_end - vector_start
            local_vector = vector_end - self.center_point
            angle = movement_vector.angle_signed(local_vector, 0.0)

            for marker in self.movement_markers:

                rotation = mathutils.Euler((0.0, 0.0, angle))
                new_position = marker.offset.copy().to_3d()
                new_position.rotate(rotation)
                target_point = self.movement_point.copy() - new_position.to_2d()

                marker.update(target_point)

    def finish(self):

        for marker in self.movement_markers:
            marker.release()


class MovementMarker(object):
    def __init__(self, manager, owner, position, offset):
        self.manager = manager
        self.owner = owner
        self.position = position
        self.offset = offset

        self.icon = particles.MovementPointIcon(self.manager, self.manager.own, position)

    def update(self, position=None):

        if position:
            self.position = position
        self.icon.set_position(self.position)

    def release(self):
        if not self.icon.invalid_location:
            if "alt" in self.manager.input.keys:
                condition = "REVERSE"
            else:
                condition = None

            if "control" in self.manager.input.keys:
                self.owner.commands.append(bgeutils.AgentCommand("ROTATION_TARGET", position=self.position, condition=condition))
            elif "shift" in self.manager.input.keys:
                self.owner.commands.append(bgeutils.AgentCommand("MOVEMENT_TARGET", position=self.position, additive=True, condition=condition))
            else:
                self.owner.commands.append(bgeutils.AgentCommand("MOVEMENT_TARGET", position=self.position, additive=False, condition=condition))
        self.icon.released = True


class GameLoop(object):
    def __init__(self, cont):
        self.debug = False
        self.console = False
        self.cont = cont
        self.own = cont.owner
        self.scene = cont.owner.scene
        self.input = game_input.GameInput()
        self.camera = camera_control.CameraControl(self)
        self.context = "PAN"
        self.mouse_timer = 6
        self.mouse_refresh = 6

        self.select_point = None
        self.movement_action = None
        self.debug_message = ""
        self.paused = False
        self.selected_agents = []

        self.level_size = 64
        self.terrain = None
        self.tiles = {}

        self.dynamic_lights = [ob for ob in self.scene.objects if ob.get("dynamic_light")]
        self.lights = []
        self.agents = []
        self.waypoints = None
        self.particles = []
        self.LOS_manager = None

        self.UI_orders = []
        self.UI_mouse_over = False

        self.cursor_refresh = 0.0
        self.tile_over = None
        self.mouse_over_unit = None

        self.debug_timer = {}

        self.state_name = None
        self.state = game_states.PrepGame(self)

    def prep_level(self):

        bge.render.setMipmapping(1)
        bge.render.setAnisotropicFiltering(2)

        vehicle_path = bge.logic.expandPath("//models/vehicles.blend")
        bge.logic.LibLoad(vehicle_path, "Scene")

        infantry_path = bge.logic.expandPath("//infantry_sprites/hre_summer_sprites.blend")
        bge.logic.LibLoad(infantry_path, "Scene")

        ground_object = bgeutils.get_ob("terrain_object", self.scene.objects)
        self.terrain = terrain_generation.TerrainGeneration(self, ground_object)
        self.LOS_manager = LOS.VisionPaint(self)

    def get_tiles(self):

        for x in range(-2, (self.level_size * 8) + 2):
            for y in range(-2, (self.level_size * 8) +2):
                point = mathutils.Vector([x, y, 0.0])
                ray = bgeutils.ground_ray(self.own, survey_point=point)
                if ray:
                    tile = bgeutils.TerrainTile(*ray)
                    terrain = self.terrain.field.get(bgeutils.get_terrain_position((x, y)), 2)
                    tile.off_road = not bool(terrain)
                else:
                    tile = bgeutils.TerrainTile(None, point, mathutils.Vector([0.0, 0.0, 1.0]))

                self.tiles[(x, y)] = tile

    def start_up(self):

        # temporary, later get heights from level generation (maybe)
        self.get_tiles()

        self.LOS_manager.do_paint()
        self.waypoints = bgeutils.Waypoints(self)

        #for i in range(2):
        #    agents.VehicleAgent(self, (103, 112 + (i * 10)), "primitive-tank", 0)

        #agents.VehicleAgent(self, (80, 130), "old tank", 1)

        squads = ["mg", "squad", "officer", "scout", "squad", "anti-tank"]

        for i in range(5):
            agents.InfantrySquad(self, (150, 90 + (i * 10)), squads[i], 0)

        #agents.InfantrySquad(self, (180, 90), "squad", 1)

        agents.TestHouse(self, (105, 88))
        agents.TestHouse(self, (156, 66))
        agents.TestHouse(self, (128, 55))

        bge.logic.globalDict['volume'] = 1.0
        bge.logic.globalDict['dirt'] = {True: ["particle_dust", [0.25, 0.18, 0.1, 2.0], 1.5],
                                        False: ["particle_ground", [0.03, 0.025, 0.027, 1.0], 1.0]}

        bge.logic.globalDict['tracks'] = [0.04, 0.027, 0.013, 3.0]

    def general_control(self):

        if self.input:
            self.input.update()
        if self.camera:
            self.camera.update()
        if self.LOS_manager:
            self.LOS_manager.update()

    def profile(self, method_name, one_time=False):

        loop_methods = {"agent_control": self.agent_control,
                        "agents_update": self.agents_update,
                        "particle_update": self.particle_update,
                        "particle_light_update": self.particle_light_update,
                        "get_cursor_location": self.get_cursor_location,
                        "general_control": self.general_control,
                        "start_up": self.start_up,
                        "prep_level": self.prep_level,
                        "agent_commands": self.agent_commands,
                        "process_UI_orders": self.process_UI_orders,
                        "main_state_machine": self.main_state_machine}

        if method_name in loop_methods:
            timer = time.clock()
            loop_methods[method_name]()

            timer = time.clock() - timer

            if one_time:
                finished = "(DONE)"
            else:
                finished = ""

            method_string = method_name

            time_string = str(round(timer * 1000, 3))
            self.debug_timer[method_name] = "{:<30}:{:>12}ms {}".format(method_string, time_string, finished)

        else:
            print("not method called [{}] on game loop".format(method_name))

    def update(self):

        self.profile("main_state_machine")

    def main_state_machine(self):
        self.state.update()

        next_state = self.state.transition()
        if next_state:
            self.state.end()
            self.state = next_state(self)
            self.state_name = next_state.__name__

    def get_light_distance(self, particle):
        if particle.object_box:
            distance = particle.object_box.getDistanceTo(self.camera.camera_hook)
        else:
            distance = particle.owner.getDistanceTo(self.camera.camera_hook)

        return distance

    def hot_keys(self):

        stance_hotkeys = ["AGGRESSIVE", "DEFEND", "SENTRY", "FLANK"]

        for stance in stance_hotkeys:
            if stance in self.input.keys:
                for agent in self.selected_agents:
                    agent.commands.append(bgeutils.AgentCommand("STANCE_CHANGE", condition=stance))

    def process_UI_orders(self):

        self.hot_keys()

        self.UI_mouse_over = False

        if not self.movement_action and not self.select_point:

            if len(self.UI_orders) > 0:
                self.UI_mouse_over = True

            for order in self.UI_orders:
                if order.name == "MINI_MAP":

                    cam_loc = order.position * (self.level_size * 8.0)
                    # quarter_turn = mathutils.Euler((0.0, 0.0, math.radians(45.0)), 'XYZ')
                    # cam_loc.rotate(quarter_turn)

                    self.camera.camera_hook.worldPosition = cam_loc

        self.UI_orders = []


    def agent_control(self):

        self.selected_agents = [agent for agent in self.agents if agent.selected]

        if len(self.selected_agents) > 0:
            self.mouse_refresh = 16
        else:
            self.mouse_refresh = 6

        right_button = "right_drag" in self.input.buttons
        left_button = "left_drag" in self.input.buttons

        if not self.UI_mouse_over:

            if right_button:
                self.mouse_refresh = 3
                self.set_movement_points(True)
            else:
                self.set_movement_points(False)

            if left_button:
                self.mouse_refresh = 3
                self.select_units(True)
            else:
                self.select_units(False)

        else:
            if not left_button:
                self.select_units(False)

            if not right_button:
                self.set_movement_points(False)

        self.number_select()

    def agent_commands(self):

        for agent in self.agents:
            agent.process_commands()

    def agents_update(self):

        next_gen_agents = []
        for agent in self.agents:
            if not agent.ended:
                next_gen_agents.append(agent)
                agent.update()

        self.agents = next_gen_agents

    def particle_update(self):
        next_generation = []
        self.lights = []

        for particle in self.particles:
            if not particle.ended:
                particle.update()
                next_generation.append(particle)
                if particle.light:
                    self.lights.append(particle)

            else:
                particle.end_object_box()

        self.particles = next_generation

    def particle_light_update(self):

        lights = self.lights
        light_casting = sorted(lights, key=lambda p_light: self.get_light_distance(p_light))

        for i in range(len(self.dynamic_lights)):
            lamp = self.dynamic_lights[i]

            if i < len(light_casting):
                light_particle = light_casting[i]
                lamp.worldPosition = light_particle.object_box.worldPosition.copy()
                lamp.energy = light_particle.light_energy
                lamp.color = light_particle.light_color
                lamp.distance = light_particle.light_distance
            else:
                lamp.energy = 0.0

    def mouse_hit_ray(self, property_string):

        screen_vect = self.camera.main_camera.getScreenVect(*self.input.virtual_mouse)
        target_position = self.camera.main_camera.worldPosition.copy() - screen_vect
        target_ray = self.camera.main_camera.rayCast(target_position, self.camera.main_camera, 1800.0, property_string, 0, 1, 0)

        return target_ray

    def set_movement_points(self, drag):

        if drag:
            if not self.movement_action:
                self.movement_action = MovementAction(self)
            else:
                self.movement_action.update()

        else:
            if self.movement_action:
                self.movement_action.finish()
                self.movement_action = None

    def get_contents(self):

        radius = 5
        half = int(round(radius * 0.5))

        enemies = []
        friends = []

        ox, oy = self.tile_over

        for x in range(radius):
            for y in range(radius):
                check_key = (ox + (x-half), oy + (y-half))
                contents = self.tiles[check_key].occupied

                if contents:
                    if contents.team != 0:
                        enemies.append(contents)
                    else:
                        friends.append(contents)

        if enemies:
            return enemies[0]
        elif friends:
            return friends[0]
        else:
            return False

    def get_cursor_location(self):

        busy = self.select_point or self.movement_action

        if self.UI_mouse_over and not busy:
            self.context = "UI"

        elif self.mouse_timer > self.mouse_refresh:
            self.mouse_timer = 0

            ground_hit = self.mouse_hit_ray("ground")
            if ground_hit[0]:
                self.tile_over = bgeutils.get_key(ground_hit[1])

            contents = self.get_contents()

            if contents:
                self.mouse_over_unit = contents
            else:
                self.mouse_over_unit = None

            context = "PAN"

            if busy:
                self.context = "SELECT"

            if self.mouse_over_unit:
                if self.mouse_over_unit.team > 0:
                    if self.mouse_over_unit.visible:
                        if self.selected_agents:
                            context = "TARGET"
                        else:
                            context = "NO_TARGET"
                else:
                    if self.mouse_over_unit.team == 0:
                        context = "SELECT"
                    else:
                        context = "NO_TARGET"

            self.context = context

        self.mouse_timer += 1

    def number_select(self):

        numbers = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]

        active_number = None
        for number in numbers:
            if number in self.input.keys:
                active_number = number

        if active_number:
            bind = "control" in self.input.keys
            additive = "shift" in self.input.keys

            for agent in self.agents:
                if agent.team == 0:
                    agent.commands.append(bgeutils.AgentCommand("NUMBER_SELECT", condition=bind, target=active_number, additive=additive))

    def select_units(self, select):

        if select:
            if not self.select_point:
                self.select_point = self.input.virtual_mouse.copy()

        else:
            if self.select_point:
                start = self.select_point
                end = self.input.virtual_mouse.copy()

                x_limit = sorted([start[0], end[0]])
                y_limit = sorted([start[1], end[1]])

                selected = None
                if self.mouse_over_unit:
                    if self.mouse_over_unit.selected:
                        self.mouse_over_unit.commands.append(bgeutils.AgentCommand("DE_SELECT"))
                    else:
                        selected = self.mouse_over_unit

                for agent in self.agents:
                    if agent.team == 0:
                        if "shift" not in self.input.keys:
                            agent.commands.append(bgeutils.AgentCommand("DE_SELECT"))

                        condition = None
                        position = None

                        if agent == selected:
                            condition = "AUTO_SELECT"
                        else:
                            position = (x_limit, y_limit)

                        agent.commands.append(bgeutils.AgentCommand("SELECT", condition=condition, position=position))

            self.select_point = None
