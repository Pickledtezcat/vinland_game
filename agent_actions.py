import bgeutils
import bge
import mathutils
import particles
import random


class VehicleTrails(object):
    def __init__(self, agent, size):
        self.manager = agent.manager
        self.agent = agent
        self.size = size
        self.timer = 0.0

        self.adders = bgeutils.get_ob_list("trail", self.agent.display_object.vehicle.childrenRecursive)
        self.number = len(self.adders)
        self.tracks = []

    def end_tracks(self):

        for track in self.tracks:
            track.dropped = True
        self.tracks = []

    def add_tracks(self, ground_normal):

        self.end_tracks()
        self.tracks = [particles.Track(self.manager, adder, ground_normal) for adder in self.adders]

    def movement_trail(self, speed):

        if self.agent.off_road:

            if self.number > 0:
                if self.timer >= 1.0:
                    self.timer = 0.0
                    for adder in self.adders:
                        particles.Dust(self.manager, adder, self.size, self.agent.off_road)
                else:
                    self.timer += (speed * 0.25)


class AgentAnimation(object):
    def __init__(self, agent, vehicle):

        self.agent = agent
        self.vehicle = vehicle

        if self.vehicle:
            self.trails = VehicleTrails(self.agent, (self.agent.stats["chassis_size"] + 1.0) * 0.5)

        self.start_hit = None
        self.end_hit = None

        self.recoil = mathutils.Vector([0.0, 0.0, 0.0])
        self.tilt = 0.0
        self.damping = 0.2
        self.slope = mathutils.Vector([0.0, 0.0, 0.0])

        self.tracks = []
        self.survey_points()

    def survey_points(self):

        if self.agent.manager.tiles[self.agent.location].off_road:
            self.agent.off_road = True
        else:
            self.agent.off_road = False

        location = self.agent.location
        target = self.agent.target_tile

        start = mathutils.Vector([location[0] + self.agent.tile_offset, location[1] + self.agent.tile_offset, 0.0])
        start_key = bgeutils.get_key(start)

        if target:
            end = mathutils.Vector([target[0] + self.agent.tile_offset, target[1] + self.agent.tile_offset, 0.0])
        else:
            end = start.copy()

        end_key = bgeutils.get_key(end)

        self.start_hit = self.agent.manager.tiles[start_key]
        self.end_hit = self.agent.manager.tiles[end_key]

        if self.vehicle:
            if self.agent.on_screen and target:
                self.trails.add_tracks(self.start_hit.normal)
            else:
                self.trails.end_tracks()

    def update(self):

        throttle = self.agent.throttle
        throttle_target = self.agent.throttle_target
        throttle_difference = (throttle - throttle_target) * 0.05

        if self.agent.reversing:
            throttle_difference *= -1.0

        throttle_difference = min(0.02, max(-0.02, throttle_difference))

        self.tilt = bgeutils.interpolate_float(self.tilt, throttle_difference, 0.03)
        self.recoil = self.recoil.lerp(mathutils.Vector([0.0, 0.0, 0.0]), self.damping * 0.1)

        point = self.agent.box.worldPosition.copy()
        start_height = self.start_hit.point.z
        end_height = self.end_hit.point.z

        if self.agent.movement:
            progress = self.agent.movement.progress
            point.z = bgeutils.interpolate_float(start_height, end_height, progress)
            normal = self.start_hit.normal.lerp(self.end_hit.normal, progress)

        else:
            point.z = start_height
            normal = self.start_hit.normal

        self.agent.hull.worldPosition = self.agent.hull.worldPosition.copy().lerp(point, 0.8)

        if self.agent.on_screen:
            self.agent.screen_position = self.agent.box.scene.active_camera.getScreenPosition(self.agent.box)

            if self.vehicle:
                local_y = self.agent.hull.getAxisVect([0.0, 1.0, 0.0])

                z = self.recoil + mathutils.Vector([0.0, self.tilt, 1.0])
                local_z = self.agent.hull.getAxisVect(z)

                target_vector = local_z.lerp(normal, self.damping)

                self.agent.hull.alignAxisToVect(local_y, 1, 1.0)
                self.agent.hull.alignAxisToVect(target_vector, 2, 1.0)

                # do slopes later
                slope = normal.copy()
                slope.z = 0.0
                self.slope = slope

                speed = self.agent.dynamic_stats["display_speed"]

                self.agent.display_object.movement_action(speed)
                self.trails.movement_trail(abs(speed))

            else:
                local_y = self.agent.hull.getAxisVect([0.0, 1.0, 0.0])
                local_z = self.agent.hull.getAxisVect([0.0, 0.0, 1.0])

                target_vector = local_z.lerp(normal, self.damping)
                self.agent.hull.alignAxisToVect(local_y, 1, 1.0)
                self.agent.hull.alignAxisToVect(target_vector, 2, 1.0)

            if self.agent.agent_type == "ARTILLERY":
                self.deploy()
        else:
            self.agent.screen_position = None

    def deploy(self):
        deploy_amount = self.agent.deployed

        for leg in self.agent.display_object.legs:
            leg_model = leg['leg']
            start = leg['start']
            end = leg['end']
            leg_model.localTransform = start.lerp(end, deploy_amount)

        gun = self.agent.display_object.gun

        if gun:
            gun_model = gun['gun']
            start = gun['start']
            end = gun['end']
            gun_model.localTransform = start.lerp(end, deploy_amount)




class AgentTargeter(object):
    def __init__(self, agent):

        self.agent = agent

        self.start = None
        self.end = None
        self.done = False
        self.progress = 0.0
        self.scale = 1.0

        self.set_up()

        if self.scale <= 0.0:
            self.done = True

    def new_facing(self):
        self.agent.old_facing = self.agent.facing

    def set_up(self):

        start_vector = self.agent.agent_hook.getAxisVect([0.0, 1.0, 0.0])
        end_vector = mathutils.Vector(self.agent.facing).to_3d()

        self.start = self.agent.agent_hook.localTransform
        self.end = end_vector.normalized().to_track_quat("Y", "Z").to_matrix().to_4x4()

        angle = start_vector.angle(end_vector)
        self.scale = angle / 3.142

    def update(self):

        if not self.done:
            self.agent.throttle_target = 0.2
            speed = self.agent.dynamic_stats.get("turning_speed", 0.02) / self.scale

            if self.progress < 1.0:
                self.progress = min(1.0, self.progress + speed)
                self.agent.agent_hook.localTransform = self.start.lerp(self.end, bgeutils.smoothstep(self.progress))
            else:
                self.new_facing()
                self.agent.throttle_target = 0.0
                self.done = True


class AgentEnemyTargeter(AgentTargeter):
    def set_up(self):

        start_vector = self.agent.agent_hook.getAxisVect([0.0, 1.0, 0.0])

        if self.agent.enemy_target:
            target_vector = self.agent.enemy_target.agent_hook.worldPosition.copy() - self.agent.agent_hook.worldPosition.copy()
        else:
            target_vector = start_vector

        end_vector = target_vector

        self.start = self.agent.agent_hook.localTransform
        self.end = end_vector.normalized().to_track_quat("Y", "Z").to_matrix().to_4x4()

        angle = start_vector.angle(end_vector)
        self.scale = angle / 3.142

    def new_facing(self):
        self.agent.exit_facing()


class AgentMovement(object):
    def __init__(self, agent):

        self.agent = agent

        if not self.agent.target_tile:
            self.done = True

        else:
            self.start = self.agent.box.worldPosition.copy()
            target = self.agent.target_tile
            self.end = mathutils.Vector([target[0] + self.agent.tile_offset, target[1] + self.agent.tile_offset, 0.0])

            self.length = (self.end - self.start).length
            self.progress = 0.0
            self.done = False

            self.agent.clear_occupied()
            self.agent.set_occupied()

    def update(self):

        if not self.done:
            self.agent.throttle_target = 1.0
            current_position = self.agent.box.worldPosition.copy()
            movement_vector = self.end - current_position

            speed = self.agent.dynamic_stats.get("speed", 0.02)
            if self.agent.extra_movement:
                speed += self.agent.extra_movement
                self.agent.extra_movement = None

            remaining = movement_vector.length

            movement_vector.length = speed
            self.agent.box.worldPosition += movement_vector

            if remaining > speed:
                self.progress = 1.0 - (remaining / self.length)
            else:
                self.agent.extra_movement = (speed - remaining)
                self.agent.location = self.agent.target_tile
                self.agent.target_tile = None
                self.done = True


class AgentPause(object):
    def __init__(self, agent, pause_length=60):

        self.agent = agent
        self.increment = 1.0 / float(pause_length)
        self.done = False
        self.progress = 0.0

    def update(self):

        if not self.done:
            self.agent.throttle_target = 0.0
            if self.progress >= 1.0:
                self.done = True
            else:
                self.progress += self.increment


class ManAction(object):
    def __init__(self, man):

        self.man = man
        self.agent = man.agent
        self.location = self.agent.location
        self.history = []
        self.occupied = None
        self.target = None
        self.destination = None
        self.start = None
        self.end = None
        self.direction = (1, 0)
        self.north = random.choice(["NE", "NW"])
        self.speed = 0.02
        self.timer = 0.0
        self.avoiding = False
        self.fidget = False
        self.go_prone = 0.0
        self.switching = 0

        self.frame = random.randint(0, 3)
        self.max_frame = 3
        self.sub_frame = random.uniform(0.0, 8.0)
        self.interval = 0.1

        self.start_up()

    def set_speed(self):
        speed = self.agent.dynamic_stats.get("speed", 0.02)
        self.speed = speed + random.uniform(0.0, 0.01)

    def update(self):

        self.switch_stance()

        if self.switching == 0:
            if self.timer >= 1.0:
                self.timer = 0.0
                self.get_next_tile()
            else:
                self.timer += self.speed
                self.man.box.worldPosition = self.start.lerp(self.end, self.timer)

        if self.agent.on_screen:
            self.animation()

    def switch_stance(self):

        if self.agent.prone and not self.man.prone:
            self.switching = 1
            if self.go_prone >= 1.0:
                self.man.prone = True

        elif not self.agent.prone and self.man.prone:
            self.switching = -1
            if self.go_prone <= 0.0:
                self.man.prone = False

        else:
            self.switching = 0

        self.go_prone = min(1.0, max(0.0, (self.go_prone + (self.speed * self.switching))))

    def frame_update(self):

        # for reference

        action_names = ["default",
                        "walk",
                        "shoot",
                        "go_prone",
                        "get_up",
                        "prone_shoot",
                        "prone_crawl",
                        "prone_death",
                        "death"]

        if self.switching != 0:
            mode = "go_prone"
        else:
            if self.man.prone:
                if self.start == self.end:
                    mode = "prone_default"
                else:
                    mode = "prone_crawl"

            else:
                if self.start == self.end:
                    mode = "default"
                else:
                    mode = "walk"

        directions_dict = {(-1, -1): "W",
                           (-1, 0): "NW",
                           (-1, 1): None,
                           (0, 1): "NE",
                           (1, 1): "E",
                           (1, 0): "SE",
                           (1, -1): "S",
                           (0, -1): "SW"}

        direction = directions_dict[self.direction]

        if not direction:
            direction = self.north

        frame = self.frame

        defaults = ["default", "prone_shoot", "trench_default"]
        switching = ["go_prone", "get_up"]

        if mode in switching:
            frame = min(3, int(self.go_prone * 4.0))

        elif mode in defaults and not self.fidget:
            frame = 0

        elif mode == "prone_default":
            frame = 0
            mode = "get_up"

        mesh_name = self.man.mesh_name
        self.man.mesh.replaceMesh("{}_{}${}_{}".format(mesh_name, mode, direction, frame))

    def animation(self):

        if self.sub_frame > self.interval:
            if self.frame < self.max_frame:
                self.frame += 1
            else:
                self.fidget = False

                if random.uniform(0.0, 1.0) > 0.9:
                    self.fidget = True

                self.frame = 0

            self.sub_frame = 0.0
            self.frame_update()

        else:
            self.sub_frame += (self.speed * 0.65)

    def start_up(self):

        start = mathutils.Vector(self.location).to_3d()
        start_hit = self.agent.manager.tiles.get(bgeutils.get_key(start))

        if start_hit:
            self.start = start_hit.point
        else:
            self.start = start

        self.get_destination()
        self.get_next_tile()
        self.frame_update()

    def get_destination(self):

        self.set_speed()

        location = self.agent.box.worldPosition.copy()
        location.z = 0.0

        offset = mathutils.Vector(self.agent.formation[self.man.index]).to_3d()
        offset.rotate(self.agent.hull.worldOrientation.copy())

        destination = (location + offset)

        self.destination = bgeutils.get_key(destination)

    def choose_tile(self):

        avoid = self.avoiding

        if len(self.history) > 15:
            self.history = []

        search_array = [(1, 0), (1, 1), (0, 1), (1, -1), (-1, 0), (-1, 1), (0, -1), (-1, -1)]

        if avoid:
            reference = bgeutils.get_key(avoid.box.worldPosition.copy())
        else:
            reference = self.destination

        current_tile = self.location
        target = current_tile
        choice = self.direction

        closest = 10000.0
        furthest = 0.0

        for s in search_array:
            neighbor = (current_tile[0] + s[0], current_tile[1] + s[1])
            if not self.check_occupied(neighbor):
                if neighbor not in self.history:

                    distance = (mathutils.Vector(reference) - mathutils.Vector(neighbor)).length
                    if bgeutils.diagonal(s):
                        distance += 0.4

                    if avoid:
                        if distance > furthest:
                            furthest = distance
                            choice = s
                            target = neighbor
                    else:
                        if distance < closest:
                            closest = distance
                            choice = s
                            target = neighbor

        self.direction = choice
        self.target = target
        self.history.append(target)

        self.clear_occupied()
        self.set_occupied(self.target)

        start = mathutils.Vector(self.location).to_3d()
        end = mathutils.Vector(self.target).to_3d()

        start_hit = self.agent.manager.tiles[bgeutils.get_key(start)]
        end_hit = self.agent.manager.tiles[bgeutils.get_key(end)]

        if start_hit and end_hit:
            self.start = start_hit.point
            self.end = end_hit.point
        else:
            self.start = start
            self.end = end

    def get_next_tile(self):

        if self.target:
            self.location = self.target
            self.start = self.end
            self.target = None

        self.get_destination()
        avoiding = self.avoiding
        self.avoiding = self.check_too_close(self.location)

        action = "CHOOSE_TILE"

        if avoiding and not self.avoiding:
            action = "WAIT"

        elif self.location == self.destination:
            if not self.avoiding:
                if self.agent.enemy_target or self.agent.agent_type == "ARTILLERY":
                    action = "FACE_TARGET"
                else:
                    action = "WAIT"

        if action == "CHOOSE_TILE":
            self.choose_tile()
        elif action == "FACE_TARGET":
            self.target = None
            self.end = self.start
            self.direction = self.agent.facing
        elif action == "WAIT":
            self.target = None
            self.end = self.start

    def check_occupied(self, target_tile):

        check_tile = self.agent.manager.tiles[target_tile].occupied

        if check_tile:
            return True

    def check_too_close(self, target_tile):

        closest = []

        radius = self.agent.avoid_radius
        half = int(round(radius * 0.5))

        ox, oy = target_tile

        for x in range(radius):
            for y in range(radius):
                check_key = (ox + (x - half), oy + (y - half))
                check_tile = self.agent.manager.tiles[check_key].occupied

                if check_tile:
                    vehicles = ["VEHICLE", "ARTILLERY"]
                    if check_tile != self.agent and check_tile.agent_type in vehicles:
                        closest.append(check_tile)

        if closest:
            return closest[0]

    def set_occupied(self, set_tile):

        self.agent.manager.tiles[set_tile].occupied = self.agent
        self.occupied = set_tile

    def clear_occupied(self):

        if self.occupied:
            self.agent.manager.tiles[self.occupied].occupied = None

        self.occupied = None


class ArtilleryManAction(ManAction):

    def check_occupied(self, target_tile):
        return False

        check_tile = self.agent.manager.tiles[target_tile].occupied

        if check_tile:
            if check_tile != self.agent:
                return True

    def check_too_close(self, target_tile):
        return False

    def set_occupied(self, set_tile):

        pass

    def clear_occupied(self):

        pass


class AgentPathfinding(object):
    def __init__(self, agent, destination):

        self.agent = agent
        self.done = False
        self.history = []

        self.destination = destination

    def next_tile(self):

        search_array = [(1, 0), (1, 1), (0, 1), (1, -1), (-1, 0), (-1, 1), (0, -1), (-1, -1)]
        current_tile = self.agent.location
        touching_infantry = False
        next_facing = None
        next_target = None
        closest = 10000.0
        free = 0

        for s in search_array:
            neighbor = (current_tile[0] + s[0], current_tile[1] + s[1])
            neighbor_check = self.agent.check_occupied(neighbor)

            if not neighbor_check:
                if neighbor not in self.history:
                    free += 1

                    distance = (mathutils.Vector(self.destination) - mathutils.Vector(neighbor)).length
                    if bgeutils.diagonal(s):
                        distance += 0.4

                    if self.agent.reversing:
                        s = (s[0] * -1, s[1] * -1)

                    if s != self.agent.facing:
                        distance += 0.2

                    if distance < closest:
                        closest = distance
                        next_facing = s
                        next_target = neighbor

            elif self.agent.agent_type != "INFANTRY":
                for agent in neighbor_check:
                    if agent.agent_type == "INFANTRY" and agent.team == self.agent.team:
                        touching_infantry = True

        return closest, next_facing, next_target, free, touching_infantry

    def update(self):
        if self.agent.stop_movement:
            if not self.agent.movement:
                self.destination = None
                self.done = True

        if self.destination:
            if not self.agent.movement:

                closest, next_facing, next_target, free, touching_infantry = self.next_tile()

                if free < 6 and closest < 6 and len(self.history) > 12:
                    self.destination = None

                elif self.agent.location == self.destination:
                    self.destination = None

                elif not next_facing:
                    self.destination = None

                elif next_target:
                    if touching_infantry:
                        self.agent.target_tile = None
                        self.agent.set_waiting()

                    else:
                        if len(self.history) > 25:
                            self.history = []

                        if next_facing != self.agent.facing:
                            self.agent.facing = next_facing
                            self.agent.set_targeter()

                        else:
                            self.history.append(next_target)
                            self.agent.target_tile = next_target
                            self.agent.set_movement()
                            self.agent.animation.survey_points()

                else:
                    self.destination = None

        if not self.destination:
            self.agent.throttle_target = 0.0
            self.done = True


class CombatControl(object):
    def __init__(self, agent):
        self.agent = agent
        self.manager = self.agent.manager

        self.turret = None

        self.refresh_timer = 0
        self.target = None
        self.get_targets()

    def get_targets(self):
        if not self.agent.enemy_target:

            target_list = [agent for agent in self.manager.agents if
                           agent.team >= 0 and agent.team != self.agent.team and agent.visible]

            closest = 90000.0
            best = None

            for target in target_list:
                distance = (target.box.worldPosition.copy() - self.agent.box.worldPosition.copy()).length

                if distance < 48.0:

                    if distance < closest:
                        closest = distance
                        best = target

            self.target = best
        else:
            self.target = self.agent.enemy_target

    def process(self):
        pass

    def visibility(self):

        if self.agent.team != 0:
            self.agent.set_visible(False)

            for agent in self.agent.manager.agents:
                if agent.team == 0:
                    distance = (self.agent.box.worldPosition.to_2d() - agent.box.worldPosition.to_2d()).length

                    if distance < 48.0:
                        self.agent.set_visible(True)

    def update(self):

        if self.refresh_timer > 30:
            self.refresh_timer = 0
            self.visibility()
            self.get_targets()
        else:
            self.refresh_timer += 1

        self.process()


class VehicleCombatControl(CombatControl):
    def __init__(self, agent):
        super().__init__(agent)

        if self.agent.stats["turret_size"] > 0:
            self.turret = self.agent.display_object.turret
            self.turret_rest = self.turret.localTransform

    def target_turret(self):

        if self.turret:
            if self.target:
                local_y = self.agent.agent_hook.getAxisVect([0.0, 1.0, 0.0]).to_2d()
                target_vector = (self.target.box.worldPosition.copy() - self.agent.box.worldPosition.copy()).to_2d()

                enemy_angle = local_y.angle_signed(target_vector, 0.0) * -1.0

                rot_mat = mathutils.Matrix.Rotation(enemy_angle, 4, "Z")
                turret_target = self.turret_rest * rot_mat

                self.turret.localTransform = self.turret.localTransform.lerp(turret_target, 0.02)

            else:
                rot_mat = mathutils.Matrix.Rotation(0.0, 4, "Z")
                turret_target = self.turret_rest * rot_mat
                self.turret.localTransform = self.turret.localTransform.lerp(turret_target, 0.02)

    def process(self):
        self.target_turret()


class InfantryCombatControl(CombatControl):
    def __init__(self, agent):
        super().__init__(agent)

    def process(self):
        pass
