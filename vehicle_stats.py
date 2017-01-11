import bge
import mathutils
import bgeutils
import vehicle_parts

class VehicleWeapon(object):

    def __init__(self, part_number, section, weapon_location):

        self.part_number = part_number
        self.section = section
        self.weapon_location = weapon_location

        parts_dict = vehicle_parts.get_vehicle_parts()
        part= parts_dict[self.part_number]






class VehicleStats(object):

    def __init__(self, chassis_size, turret_size, contents, faction_number=0):

        self.chassis_size = chassis_size
        self.turret_size = turret_size
        self.contents = contents

        self.faction_number = faction_number

        self.on_road_speed = 0
        self.off_road_speed = 0
        self.on_road_handling = 0
        self.off_road_handling = 0
        self.reverse_speed_mod = 0

        self.drive_type = "WHEELED"
        self.suspension_type = "UNSPRUNG"
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
        self.reliability = 0
        self.cost = 0

        self.flags = []
        self.armor = dict(TURRET=0, FRONT=0, FLANKS=0)
        self.crits = dict(TURRET=[], FRONT=[], FLANKS=[])
        self.weapons = []
        self.durability = 0

        self.artillery = False
        self.invalid = []

        self.generate_stats()

    def generate_stats(self):

        parts = {}

        for content_key in self.contents:
            tile = self.contents[content_key]

            if tile.parent_tile == content_key:
                part = self.contents[tile.parent_tile].part
                location = tile.location
                weapon_location = tile.weapon_location

                parts[tile.parent_tile] = {"part": part, "location": location, "weapon_location": weapon_location}
                self.flags = bgeutils.add_entry(part['flags'], self.flags)

        if "GUN_CARRIAGE" in self.flags:
            self.build_artillery(parts)
        else:
            self.build_vehicle(parts)

    def build_vehicle(self, parts):

        parts_dict = vehicle_parts.get_vehicle_parts()
        chassis_armor_scale = vehicle_parts.chassis_dict[self.chassis_size]["armor_scale"]
        turret_armor_scale = vehicle_parts.chassis_dict[self.turret_size]["armor_scale"]

        engine_handling = 0
        suspension = 0
        fuel = 0.0
        ammo = 0.0
        armor_coverage = False

        sorted_parts = sorted(parts, key=lambda my_key: parts[my_key].get("rating", 0))

        sections = ["FRONT", "FLANKS", "TURRET"]
        section_dict = {section: {"armor": 0, "manpower": 0, "crits":[]} for section in sections}

        for part_key in sorted_parts:

            location = parts[part_key]["location"]
            part_number = parts[part_key]["part"]
            part = parts_dict[part_number]
            part_type = part.get("part_type", None)
            rating = part.get("rating", 0)
            flag = part.get("flags")
            weight = part.get("weight", 0)

            if part_type == "crew":
                self.weight += (weight * 0.5)
                self.crew += 1
                section_dict[location]["manpower"] += rating

            if part == "armor":
                if location == "TURRET":
                    armor_scale = turret_armor_scale
                else:
                    armor_scale = chassis_armor_scale

                if section_dict[location]['armor'] < 1:
                    section_dict[location]['armor'] += rating
                else:
                    section_dict[location]['armor'] += (rating * 0.5)

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
            part_number = parts[part_key]["part"]
            part = parts_dict[part_number]
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

            self.cost += ((5 + level) * 100) * bulk
            self.durability += durability

            if part_type == "design":
                drive_types = ["WHEELED", "HALFTRACK", "TRACKED"]
                if flag in drive_types:
                    suspension += rating
                    self.drive_type = flag

            if part_type == "engine":

                if self.engine_rating == 0:
                    fuel += 0.5
                    self.engine_rating += rating
                    engine_handling += (rating * 0.5)
                else:
                    self.engine_rating += rating * 0.5

            if part_type == "suspension":
                self.suspension_type = flag
                suspension += rating

            if part_type == "weapon":
                self.ammo += 0.5

                # TODO add weapon object here
                self.weapons.append(part)

        for section in section_dict:
            pass


    def build_artillery(self, parts):
        pass




