import bge
from mathutils import Vector, Matrix
import bgeutils
import vehicle_parts


class VehicleModel(object):
    def __init__(self, adder, stats, scale=1.0, cammo=0):

        self.adder = adder
        self.scene = self.adder.scene
        self.stats = stats
        self.scale = scale
        self.parts_dict = vehicle_parts.get_vehicle_parts()

        faction_icons = {1: 0,
                         2: 2,
                         3: 1,
                         4: 3,
                         5: 5,
                         6: 4}

        icon = faction_icons[self.stats["faction_number"]]

        color = [icon * 0.25, 0.0, cammo * 0.125, 1.0]

        fast = ["CONICAL_SPRING", "BELL_CRANK", "TORSION_BAR", "HYDRAULIC", "PNEUMATIC"]
        drive_display = {"WHEELED": 0, "HALFTRACK": 1, "TRACKED": 2}

        factions = {0: [2, 5], 1: [1, 4], 2: [3, 6]}

        drive_number = drive_display[self.stats["drive"]]

        chassis_size = self.stats["chassis_size"] - 1
        turret_size = self.stats["turret_size"] - 1

        speed = "A"

        if drive_number == 2:
            if self.stats["suspension"] in fast:
                speed = "B"

        faction_number = 0
        gun_faction = 0

        if "AMPHIBIOUS" in self.stats["flags"]:
            faction_number = 3
            speed = "A"

        else:
            for faction_key in factions:
                faction_list = factions[faction_key]
                if self.stats["faction_number"] in faction_list:
                    faction_number = faction_key
                    gun_faction = faction_key

        layout = 0
        weapon_list = [len(self.stats["weapons"][location_key]) for location_key in self.stats["weapons"]]
        has_weapons = sum(weapon_list) > 0

        if turret_size >= 0:
            if self.stats["armor_scale"] > 1.0:
                layout = 2
            else:
                layout = 1

        elif self.stats["open_top"]:
            layout = 3

        elif self.stats["armor_scale"] > 0.0 or "MANTLET" in self.stats["flags"]:
            if "SUPERSTRUCTURE" in self.stats["flags"]:
                layout = 4
            elif self.stats["armor_scale"] > 1.0:
                layout = 2
            else:
                layout = 1

        elif has_weapons or self.stats["armored"]:
            layout = 1

        chassis_string = "v_chassis_{}_{}_{}_{}{}".format(chassis_size, drive_number, layout, faction_number, speed)

        self.vehicle = self.scene.addObject(chassis_string, self.adder, 0)
        self.vehicle.setParent(self.adder)

        self.tracks = bgeutils.get_ob_list("tracks", self.vehicle.children)
        if self.tracks:
            for track in self.tracks:
                mesh = track.meshes[0]

                bgeutils.bge.logic.globalDict["lib"] = bgeutils.bge.logic.globalDict.get("lib", 0)

                new_name = "lib_new_mesh_{}".format(bgeutils.bge.logic.globalDict["lib"])
                new_mesh = bgeutils.bge.logic.LibNew(new_name, "Mesh", [mesh.name])
                bgeutils.bge.logic.globalDict["lib"] += 1
                track.replaceMesh(new_mesh[0])

        self.wheels = bgeutils.get_ob_list("wheels", self.vehicle.children)

        self.turret = None

        if turret_size >= 0:

            if "AA_MOUNT" in self.stats["flags"]:
                turret_number = 1

            elif self.stats["open_turret"]:
                if self.stats["armor_scale"] > 1.0:
                    turret_number = 3
                else:
                    turret_number = 2

            elif "SLOPED" in self.stats["flags"]:
                if self.stats["armor_scale"] > 1.0:
                    turret_number = 9
                else:
                    turret_number = 8

            elif "SLOPED" in self.stats["flags"]:
                if self.stats["armor_scale"] > 1.0:
                    turret_number = 9
                else:
                    turret_number = 8

            elif self.stats["suspension"] in fast:
                if self.stats["armor_scale"] > 1.0:
                    turret_number = 7
                else:
                    turret_number = 6

            else:
                if self.stats["armor_scale"] > 1.0:
                    turret_number = 5
                else:
                    turret_number = 4

            antenna = 0
            if "ANTENNA" in self.stats["flags"]:
                antenna = 1

            turret_string = "v_turret_{}_{}_{}".format(turret_number, turret_size, antenna)

            self.turret_adder = bgeutils.get_ob("turret", self.vehicle.children)
            turret = self.scene.addObject(turret_string, self.turret_adder, 0)
            turret.setParent(self.vehicle)
            self.turret = turret

        self.gun_adders = {}
        adders = ["left_gun", "right_gun", "back_gun", "front_gun", "turret_gun"]

        for g_adder in adders:
            self.get_adders(g_adder)

        if layout > 0:

            if "OPEN_TOP" in self.stats["flags"] and turret_size < 1:
                o_adder = self.gun_adders["front_gun"][0]
                gun_block_string = "v_gun_block_{}_{}".format(gun_faction, chassis_size)
                gun_block = o_adder.scene.addObject(gun_block_string, o_adder, 0)
                gun_block.setParent(o_adder)
                self.get_adders("front_gun", parent=o_adder, parent_key="mount_gun")

            if "OPEN_TURRET" in self.stats["flags"] and turret_size > 0:
                ot_adder = self.gun_adders["turret_gun"][0]
                gun_block_string = "v_gun_block_{}_{}".format(gun_faction, turret_size)
                gun_block = ot_adder.scene.addObject(gun_block_string, ot_adder, 0)
                gun_block.setParent(ot_adder)
                self.get_adders("turret_gun", parent=ot_adder, parent_key="mount_gun")

            if "SPONSON" in self.stats["flags"]:

                sponson_locations = [("FRONT", "front_gun"), ("LEFT", "left_gun"), ("RIGHT", "right_gun"),
                                     ("BACK", "back_gun")]

                for sponson_location in sponson_locations:
                    adder_key = sponson_location[1]
                    weapon_key = sponson_location[0]
                    if len(self.stats["weapons"][weapon_key]) > 0:
                        c_adder = self.gun_adders[adder_key][0]
                        mantlet_string = "v_mantlet_{}_{}".format(3, chassis_size)
                        mantlet = c_adder.scene.addObject(mantlet_string, c_adder, 0)
                        mantlet.setParent(c_adder)
                        self.get_adders(adder_key, parent=c_adder, parent_key="sponson_gun")

            if "MANTLET" in self.stats["flags"] and turret_size > 0:
                t_adder = self.gun_adders["turret_gun"][0]
                mantlet_string = "v_mantlet_{}_{}".format(gun_faction, turret_size)
                mantlet = t_adder.scene.addObject(mantlet_string, t_adder, 0)
                mantlet.setParent(t_adder)
                self.get_adders("turret_gun", parent=t_adder, parent_key="mount_gun")

            sections = [("FRONT", "front_gun"), ("LEFT", "left_gun"), ("RIGHT", "right_gun"), ("BACK", "back_gun"),
                        ("TURRET", "turret_gun")]

            for section in sections:
                location = section[0]
                weapons = [ob for ob in self.stats["weapons"][location] if ob["flags"] != "ROCKETS"]
                weapons = sorted(weapons, key=lambda s_weapon: s_weapon["visual"])
                weapons.reverse()
                adders = self.gun_adders.get(section[1])
                if adders:

                    weapons_length = len(weapons)

                    if "FUEL" in self.stats["flags"] and weapons_length < 1:
                        if section[0] == "LEFT" or section[0] == "RIGHT":
                            fuel_string = "v_fuel_tank_{}".format(chassis_size)
                            f_adder = adders[0]
                            fuel_tank = f_adder.scene.addObject(fuel_string, f_adder, 0)
                            fuel_tank.setParent(self.vehicle)

                    for i in range(weapons_length):
                        if i < len(adders):
                            w_adder = adders[i]
                            weapon = weapons[i]
                            gun_size = weapon["visual"]
                            gun_string = "v_gun_{}_{}".format(gun_faction, gun_size)

                            gun = w_adder.scene.addObject(gun_string, w_adder, 0)
                            if location == "TURRET":
                                gun.setParent(self.turret)
                            else:
                                gun.setParent(self.vehicle)

        crew_adders = bgeutils.get_ob_list("crew_man", self.vehicle.childrenRecursive)
        for crew_adder in crew_adders:
            if crew_adder.get("standing"):
                add_ob = "standing_crew_man"
            else:
                add_ob = "crew_man"

            crew_man = crew_adder.scene.addObject(add_ob, crew_adder, 0)
            crew_man.setParent(crew_adder)

        self.hatch = None
        commander_flags = ["COMMANDER", "COMMANDERS_CUPOLA", "NIGHT_VISION_CUPOLA"]
        has_commander = False

        for commander_flag in commander_flags:
            if commander_flag in self.stats["flags"]:
                has_commander = True

        if "ROCKET_MOUNT" in self.stats["flags"]:
            if self.stats["turret_size"] > 0:
                attach_point = self.turret
                rocket_size = turret_size
            else:
                attach_point = self.vehicle
                rocket_size = chassis_size

            rocket_adder = bgeutils.get_ob("turret", attach_point.children)
            if rocket_adder:
                rocket_armor = 0
                if self.stats["armor_scale"] > 1.0:
                    rocket_armor = 1

                rocket_turret = "v_turret_0_{}_{}".format(rocket_size, rocket_armor)
                self.rocket_turret = rocket_adder.scene.addObject(rocket_turret, rocket_adder, 0)
                self.rocket_turret.setParent(attach_point)

        elif has_commander:
            if self.stats["turret_size"] > 0:
                attach_point = self.turret
            else:
                attach_point = self.vehicle

            hatch_adder = bgeutils.get_ob("turret", attach_point.children)
            if hatch_adder:

                if hatch_adder.get("small"):
                    hatch_size = "s"
                else:
                    hatch_size = "l"

                if hatch_adder.get("square"):
                    hatch_shape = "s"
                else:
                    hatch_shape = "r"

                if "COMMANDERS_CUPOLA" in self.stats["flags"] or "NIGHT_VISION_CUPOLA" in self.stats["flags"]:
                    if hatch_size == "s":
                        self.open_hatch = "small_cupola"
                        self.closed_hatch = "small_cupola"
                    else:
                        self.open_hatch = "large_cupola"
                        self.closed_hatch = "large_cupola"
                else:
                    self.open_hatch = "hatch_{}_o_{}".format(hatch_size, hatch_shape)
                    self.closed_hatch = "hatch_{}_c_{}".format(hatch_size, hatch_shape)

                self.hatch = hatch_adder.scene.addObject(self.open_hatch, hatch_adder, 0)
                self.hatch.setParent(attach_point)

                if "NIGHT_VISION_CUPOLA" in self.stats["flags"]:
                    night_scope = hatch_adder.scene.addObject("v_night_scope", hatch_adder, 0)
                    night_scope.setParent(self.hatch)

        self.vehicle.color = color
        for ob in self.vehicle.childrenRecursive:
            ob.color = color

        self.vehicle.localScale *= scale

    def get_adders(self, adder_string, parent=None, parent_key=None):
        if not parent:
            parent = self.vehicle
            adder_list = bgeutils.get_ob_list(adder_string, parent.childrenRecursive)
            adder_list = [[ob[adder_string], ob] for ob in adder_list]
            adder_list = sorted(adder_list)

        else:
            adder_list = bgeutils.get_ob_list(parent_key, parent.childrenRecursive)
            adder_list = [[ob[parent_key], ob] for ob in adder_list]
            adder_list = sorted(adder_list)

        if adder_list:
            adder_list = [ob[1] for ob in adder_list]

        self.gun_adders[adder_string] = adder_list

    def end_vehicle(self):
        self.vehicle.endObject()

    def movement_action(self, speed):

        for wheel in self.wheels:
            wheel.applyRotation([-speed, 0.0, 0.0], 1)

        for track in self.tracks:
            mesh = track.meshes[0]
            transform = bgeutils.Matrix.Translation((speed * 0.01, 0.0, 0.0))
            mesh.transformUV(0, transform)

    def preview_update(self, rotation):

        if self.vehicle:

            initial_transform = self.adder.worldTransform
            mat_rotation = bgeutils.Matrix.Rotation(bgeutils.math.radians(360.0 * rotation), 4, "Z")

            self.vehicle.worldTransform = initial_transform * mat_rotation
            self.vehicle.localScale = [self.scale, self.scale, self.scale]

            if self.turret:
                self.turret.applyRotation([0.0, 0.0, 0.001], 1)

            for ob in self.wheels:
                ob.applyRotation([-0.05, 0.0, 0.0], 1)

            for ob in self.tracks:
                mesh = ob.meshes[0]
                transform = bgeutils.Matrix.Translation((0.001, 0.0, 0.0))
                mesh.transformUV(0, transform)


class ArtilleryModel(object):
    def __init__(self, adder, stats, scale=1.0, cammo=0):

        self.adder = adder
        self.scene = self.adder.scene
        self.stats = stats
        self.scale = scale
        self.parts_dict = vehicle_parts.get_vehicle_parts()

        self.display_cycle = 0.0
        self.cycling = False

        faction_icons = {1: 0,
                         2: 2,
                         3: 1,
                         4: 3,
                         5: 5,
                         6: 4}

        icon = faction_icons[self.stats["faction_number"]]

        color = [icon * 0.25, 0.0, cammo * 0.125, 1.0]

        all_weapons = self.stats["weapons"]["FRONT"]

        model = "light_machine_gun"

        if all_weapons:
            weapon = all_weapons[0]
            flags = self.stats['flags']
            weapon_rating = weapon['rating']

            if "AA_MOUNT" in flags:
                if weapon_rating > 9:
                    model = "heavy_aa"
                elif weapon_rating > 3:
                    model = "medium_aa"
                else:
                    model = "light_aa"

            elif "ROCKET_MOUNT" in flags:

                weapons = self.stats["weapons"]["FRONT"]
                total_rating = 0
                for w in weapons:
                    total_rating += w['rating']

                if total_rating > 25:
                    model = "heavy_rocket_launcher"
                elif total_rating > 15:
                    model = "medium_rocket_launcher"
                else:
                    model = "light_rocket_launcher"

            else:
                artillery = ["LOW_VELOCITY", "NO_SIGHTS"]

                if weapon['flags'] == "MORTAR":
                    if weapon_rating < 10:
                        model = "light_mortar"
                    else:
                        model = "heavy_mortar"
                elif weapon['flags'] in artillery:
                    if weapon_rating > 14:
                        model = "heavy_artillery"
                    elif weapon_rating > 9:
                        model = "medium_artillery"
                    else:
                        model = "light_artillery"

                else:
                    if weapon_rating > 9:
                        model = "heavy_anti_tank_gun"
                    elif weapon_rating > 5:
                        model = "medium_anti_tank_gun"
                    elif weapon_rating > 2:
                        model = "light_anti_tank_gun"
                    # else:
                    #     model = "heavy_machine_gun"

        self.vehicle = self.scene.addObject(model, self.adder, 0)
        self.vehicle.worldPosition.z += 0.2
        self.vehicle.setParent(self.adder)

        crew_adders = bgeutils.get_ob_list("crew", self.vehicle.children)

        for crew_adder in crew_adders:
            crew_man = crew_adder.scene.addObject("artillery_crewman", crew_adder, 0)
            crew_man.setParent(crew_adder)

        legs = bgeutils.get_ob_list("leg", self.vehicle.children)
        self.legs = []

        for leg in legs:
            if leg.children != []:
                end = bgeutils.get_ob("deployed_position", leg.children)
                if end:
                    leg_set = {'leg': leg, 'start': leg.localTransform, "end": end.localTransform}
                    end.endObject()
                    self.legs.append(leg_set)

        self.gun = None
        gun = bgeutils.get_ob("gun", self.vehicle.children)

        if gun:
            if gun.children:
                end = bgeutils.get_ob("deployed_position", gun.children)
                if end:
                    gun_set = {'gun': gun, 'start': gun.localTransform, "end": end.localTransform}
                    end.endObject()
                    self.gun = gun_set

        self.wheels = bgeutils.get_ob_list("wheels", self.vehicle.children)
        self.turret = bgeutils.get_ob("turret", self.vehicle.children)
        self.tracks = []

        self.vehicle.color = color
        for ob in self.vehicle.childrenRecursive:
            ob.color = color

        self.vehicle.localScale *= scale

    def end_vehicle(self):
        self.vehicle.endObject()

    def movement_action(self, speed):

        for wheel in self.wheels:
            wheel.applyRotation([-speed, 0.0, 0.0], 1)

        for track in self.tracks:
            mesh = track.meshes[0]
            transform = bgeutils.Matrix.Translation((speed * 0.01, 0.0, 0.0))
            mesh.transformUV(0, transform)

    def preview_update(self, rotation):

        if self.vehicle:

            if self.cycling:
                if self.display_cycle < 1.0:
                    self.display_cycle += 0.01
                else:
                    self.cycling = False
            else:
                if self.display_cycle > 0.0:
                    self.display_cycle -= 0.01
                else:
                    self.cycling = True

            initial_transform = self.adder.worldTransform
            mat_rotation = bgeutils.Matrix.Rotation(bgeutils.math.radians(360.0 * rotation), 4, "Z")

            self.vehicle.worldTransform = initial_transform * mat_rotation
            self.vehicle.localScale = [self.scale, self.scale, self.scale]

            if self.turret:
                self.turret.applyRotation([0.0, 0.0, 0.001], 1)

            for ob in self.wheels:
                ob.applyRotation([-0.05, 0.0, 0.0], 1)

            for ob in self.tracks:
                mesh = ob.meshes[0]
                transform = bgeutils.Matrix.Translation((0.001, 0.0, 0.0))
                mesh.transformUV(0, transform)

            for leg in self.legs:
                leg['leg'].localTransform = leg['start'].lerp(leg['end'], bgeutils.smoothstep(self.display_cycle))

            if self.gun:
                self.gun['gun'].localTransform = self.gun['start'].lerp(self.gun['end'], bgeutils.smoothstep(self.display_cycle))

