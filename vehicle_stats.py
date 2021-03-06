import bge
import mathutils
import bgeutils
import vehicle_parts
import json


def save_vehicle(vehicle_dict, chassis_size, turret_size, contents, save_name, faction_number):
    current_contents = {"{}&{}".format(key[0], key[1]): contents[key].__dict__ for key in
                        contents}

    new_vehicle = {"name": save_name,
                   "chassis_size": chassis_size,
                   "turret_size": turret_size,
                   "faction_number": faction_number,
                   "contents": current_contents}

    vehicle_dict[save_name] = new_vehicle

    out_path = bge.logic.expandPath("//vehicles/saved_vehicles.txt")
    with open(out_path, "w") as outfile:
        json.dump(vehicle_dict, outfile)


class VehicleTile(object):
    def __init__(self, x, y, location, weapon_location):
        self.x = x
        self.y = y

        self.part = None
        self.location = location
        self.weapon_location = weapon_location
        self.parent_tile = None
        self.rotated = False


def load_vehicle(load_name):

    def construct_tile(tile):
        new_tile = VehicleTile(tile["x"], tile["y"], tile["location"], tile["weapon_location"])
        new_tile.part = tile["part"]
        new_tile.parent_tile = tile["parent_tile"]
        new_tile.rotated = tile["rotated"]

        return new_tile

    in_path = bge.logic.expandPath("//vehicles/saved_vehicles.txt")

    with open(in_path, "r") as infile:
        vehicle_dict = json.load(infile)

    if load_name in vehicle_dict:
        vehicle = vehicle_dict[load_name]

        contents = vehicle['contents']
        chassis_size = vehicle["chassis_size"]
        turret_size = vehicle["turret_size"]
        faction_number = vehicle["faction_number"]

        tiles = [construct_tile(tile) for tile in contents]
        vehicle_stats = VehicleStats(chassis_size, turret_size, tiles, faction_number)

        return vehicle_stats

    return None


class VehicleWeapon(object):

    def __init__(self, part, section, weapon_location):

        self.part = part
        self.section = section
        self.weapon_location = weapon_location

        self.name = self.part['name']
        self.visual = self.part['visual']
        self.rating = self.part['rating']
        self.flags = self.part['flags']

        self.rate_of_fire = 0
        self.emitter = None

    def set_emitter(self, emitter):
        self.emitter = emitter

    def update(self):
        pass


class VehicleStats(object):

    def __init__(self, chassis_size, turret_size, contents, faction_number):

        self.chassis_size = chassis_size
        self.turret_size = turret_size
        self.contents = contents
        self.faction_number = faction_number

        self.speed = []
        self.handling = []
        self.reverse_speed_mod = 0

        self.drive_type = "WHEELED"
        self.suspension_type = "UNSPRUNG"
        self.suspension_rating = 0
        self.engine_handling = 0
        self.unsupported_weight = 0
        self.engine_rating = 0
        self.stability = 0
        self.vision_distance = 1
        self.turret_speed = 0

        self.weight = 0
        self.crew = 0
        self.range = 0
        self.stores = 0
        self.ammo = 0
        self.fuel = 0
        self.reliability = 0
        self.cost = 0

        self.flags = []
        self.armor = dict(TURRET=0, FRONT=0, FLANKS=0)
        self.manpower = dict(TURRET=0, FRONT=0, FLANKS=0)
        self.crits = dict(TURRET=[], FRONT=[], FLANKS=[])
        self.weapons = []
        self.durability = 0
        self.armored = False
        self.open_top = False

        self.artillery = False
        self.invalid = []

        self.generate_stats()

    def generate_stats(self):

        parts_dict = vehicle_parts.get_vehicle_parts()
        parts = {}

        for content_key in self.contents:
            tile = self.contents[content_key]

            if tile.parent_tile == content_key:
                part_key = self.contents[tile.parent_tile].part
                part = parts_dict[part_key]
                location = tile.location
                weapon_location = tile.weapon_location
                part_type = part.get("part_type", None)

                parts[tile.parent_tile] = {"part": part, "location": location, "weapon_location": weapon_location}

                if part_type != "weapon":
                    self.flags = bgeutils.add_entry(part['flags'], self.flags)

        self.build_vehicle(parts)

    def build_vehicle(self, parts):

        chassis_armor_scale = vehicle_parts.chassis_dict[self.chassis_size]["armor_scale"]
        turret_armor_scale = vehicle_parts.turret_dict[self.turret_size]["armor_scale"]

        sorted_parts = sorted(parts, key=lambda my_key: parts[my_key].get("rating", 0))

        for part_key in sorted_parts:

            location = parts[part_key]["location"]
            part = parts[part_key]["part"]
            part_type = part.get("part_type", None)
            rating = part.get("rating", 0)
            flag = part.get("flags")
            weight = part.get("weight", 0)

            if part_type == "crew":
                self.weight += (weight * 0.5)
                self.crew += 1
                self.manpower[location] += rating

            if part_type == "armor":
                if location == "TURRET":
                    armor_scale = turret_armor_scale
                else:
                    armor_scale = chassis_armor_scale

                if self.armor[location] < 1:
                    self.armor[location] += rating
                else:
                    self.armor[location] += (rating * 0.5)

                weight *= armor_scale
                self.weight += weight

                spalling = ["CAST", "RIVETED", "THIN"]
                if flag in spalling:
                    self.flags = bgeutils.add_entry("SPALLING", self.flags)

            else:
                self.weight += weight

        for part_key in sorted_parts:

            location = parts[part_key]["location"]
            weapon_location = parts[part_key]["weapon_location"]
            part = parts[part_key]["part"]
            part_type = part.get("part_type", None)

            x_size = part.get("x_size")
            y_size = part.get("y_size")
            bulk = x_size * y_size

            crit = part.get("critical")

            for c in range(bulk):
                self.crits[location].append(crit)

            flag = part.get("flags")
            rating = part.get("rating", 0)
            durability = part.get("durability", 0)
            level = part.get("level", 0)

            self.cost += ((5 + level) * 10) * bulk
            self.durability += durability

            if part_type == "design":
                drive_types = ["WHEELED", "HALFTRACK", "TRACKED"]
                if flag in drive_types:
                    self.suspension_rating += rating
                    self.drive_type = flag

            if part_type == "engine":

                if self.engine_rating == 0:
                    self.fuel += 0.5
                    self.engine_rating += rating
                    self.engine_handling += (rating * 0.5)
                else:
                    self.engine_rating += rating * 0.5

            if part_type == "suspension":
                self.suspension_type = flag
                self.suspension_rating += rating

            if part_type == "weapon":
                self.ammo += 0.5

                weapon = VehicleWeapon(part, location, weapon_location)
                self.weapons.append(weapon)

            else:
                # TODO add more flags
                if "AMMO" in self.flags:
                    self.ammo += 1.0
                if "FUEL" in self.flags:
                    self.fuel += 1.0

        for section_key in self.armor:
            self.armor[section_key] = int(round(self.armor[section_key], 0))
            section_armor = self.armor[section_key]
            if section_armor > 0 or "ARMORED_CHASSIS" in self.flags:
                self.armored = True

        if "GUN_CARRIAGE" in self.flags:
            self.get_gun_movement()
        else:
            self.get_vehicle_movement()

        self.get_vision()

    def get_gun_movement(self):
        pass

    def get_vehicle_movement(self):

        suspension_dict = vehicle_parts.suspension_dict
        drive_dict = vehicle_parts.drive_dict
        power_to_weight = round((self.engine_rating * 50) / max(1, self.weight), 1)

        drive_mods = drive_dict[self.drive_type]
        suspension_mods = suspension_dict[self.suspension_type]

        stability = suspension_mods["stability"] + drive_mods["stability"]
        on_road_handling = suspension_mods["handling"][0] + drive_mods["handling"][
            0] + self.engine_handling
        off_road_handling = suspension_mods["handling"][1] + drive_mods["handling"][
            1] + self.engine_handling

        tonnage_mod = int(self.weight * 0.1)

        on_road_handling -= tonnage_mod
        off_road_handling -= tonnage_mod

        on_road_speed = min(99, (power_to_weight * suspension_mods["on_road"]) * drive_mods["on_road"])
        off_road_speed = min(50, (power_to_weight * suspension_mods["off_road"]) * drive_mods["off_road"])

        if self.suspension_rating < self.weight:
            if self.suspension_rating <= 0:
                weight_scale = 0.0
            else:
                weight_scale = self.suspension_rating / self.weight

            on_road_speed = int(on_road_speed * weight_scale)
            off_road_speed = int(off_road_speed * weight_scale)
            on_road_handling = int(on_road_handling * weight_scale)
            off_road_handling = int(off_road_handling * weight_scale)

        on_road_handling = max(1, on_road_handling)
        off_road_handling = max(1, off_road_handling)

        self.stability = stability
        self.handling = [on_road_handling, off_road_handling]
        self.speed = [on_road_speed, off_road_speed]

    def get_vision(self):

        vision_distance = 1
        good_vision = False
        great_vision = False

        if "OPEN_TOP" in self.flags:
            good_vision = True
            self.open_top = True

        if self.turret_size > 0:
            if "OPEN_TOP" in self.flags:
                great_vision = True
            else:
                good_vision = True

        if "COMMANDER" in self.flags:
            if self.turret_size > 0:
                great_vision = True
            else:
                good_vision = True

        if "COMMANDERS_CUPOLA" in self.flags:
            if self.turret_size > 0:
                great_vision = True
            else:
                good_vision = True

        if not self.armored:
            vision_distance += 1

        if great_vision:
            vision_distance += 2

        elif good_vision:
            vision_distance += 1

        if "NIGHT_VISION_CUPOLA" in self.flags:
            vision_distance += 1

        self.vision_distance = vision_distance

    def build_artillery(self, parts):
        pass




