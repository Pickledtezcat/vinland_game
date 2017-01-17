import bge
import buildutils
import bgeutils
import random
import game_input
import vehicle_parts
import vehicle_stats
import mathutils
import math

import model_display
import json


class BaseBuilder(object):
    def __init__(self, manager):
        self.manager = manager
        self.debug = True
        self.cont = self.manager.cont
        self.own = self.cont.owner
        self.scene = self.cont.owner.scene
        self.input = game_input.GameInput()
        self.main_camera = self.scene.active_camera

        if self.manager.contents:
            self.contents = self.manager.contents
            self.chassis_size = self.manager.chassis_size
            self.turret_size = self.manager.turret_size
            self.stats = self.manager.stats
        else:
            self.contents = {}
            self.chassis_size = 1
            self.turret_size = 0
            self.stats = None

        self.mode_change = None
        self.left_button = False
        self.right_button = False

        self.parts_dict = vehicle_parts.get_vehicle_parts()
        self.chassis_dict = vehicle_parts.chassis_dict
        self.turret_dict = vehicle_parts.turret_dict
        self.suspension_dict = vehicle_parts.suspension_dict
        self.drive_dict = vehicle_parts.drive_dict
        self.color_dict = vehicle_parts.color_dict

        self.tech_level_dict = self.get_tech_levels()

        self.mouse = self.scene.addObject("mouse_pointer", self.own, 0)
        self.mouse_text = bgeutils.get_ob("info_text", self.mouse.children)
        self.mouse_text.color = [1.0, 0.8, 0.0, 1.0]
        self.mouse_text_shadow = bgeutils.get_ob("shadow", self.mouse.children)
        self.mouse_text_shadow.color = [0.0, 0.0, 0.01, 1.0]
        self.mouse_text_shadow.localScale = [0.0, 0.0, 0.0]

        self.background = None

    def get_tech_levels(self):

        def get_level(pair, turn):
            level, increment = pair

            for i in range(turn):
                level += increment

            return int(round(level))

        tech_levels = vehicle_parts.tech_levels[self.manager.faction]
        tech_level_dict = {tech_key: get_level(tech_levels[tech_key], self.manager.game_turn) for tech_key in
                           tech_levels}

        return tech_level_dict

    def preserve_contents(self):

        self.manager.contents = self.contents
        self.manager.stats = self.stats
        self.manager.chassis_size = self.chassis_size
        self.manager.turret_size = self.turret_size

    def mouse_hit_ray(self, string_property):
        screen_vect = self.main_camera.getScreenVect(*self.input.virtual_mouse)
        target_position = self.main_camera.worldPosition.copy() - screen_vect
        target_ray = self.main_camera.rayCast(target_position, self.main_camera, 1800.0, string_property, 0, 1, 0)

        return target_ray

    def part_description(self, part):

        description = buildutils.split_string_in_lines(part["description"], 24)
        size = "SIZE:_({},_{})".format(part["x_size"], part["y_size"])
        note = ""

        if part["location"] == -1:
            note = "{}\n*CHASSIS_ONLY.".format(note)
        if part["location"] == 1:
            note = "{}\n*TURRET_ONLY.".format(note)
        if part["location"] == 2:
            note = "{}\n*TURRET-LESS_VEHICLES_ONLY.".format(note)

        tons = "TON"
        if part["weight"] > 1.0 or part["weight"] < 1.0:
            tons = "TONS"

        weight = "{}_{}".format(part["weight"], tons)
        if part["rating"] != 0:
            rating = "RATING:_{}".format(part["rating"])
        else:
            rating = ""
        help_text = "{}\n{}\n{}\n{}{}".format(size, weight, rating, description, note)

        return help_text

    def clean_up(self):
        if self.background:
            self.background.endObject()
        self.mouse.endObject()

    def process_mode(self):

        if "left_button" in self.input.buttons:
            self.left_button = True
        else:
            self.left_button = False

        if "right_button" in self.input.buttons:
            self.right_button = True
        else:
            self.right_button = False

        if self.mode_change:
            self.clean_up()
            return self.mode_change

        else:
            self.input.update()
            self.mouse_pointer()

    def mouse_pointer(self):
        pass


class SaveMode(BaseBuilder):
    def __init__(self, manager):
        super().__init__(manager)

        self.background = self.scene.addObject("save_background", self.own, 0)
        self.background.worldPosition.z -= 0.1

        self.option_buttons = bgeutils.get_ob("option_buttons", self.background.children)
        self.vehicle_name_box = None

        self.refresh_controls = True
        self.buttons = []

    def clean_up(self):
        super().clean_up()

        self.clean_buttons()

    def clean_buttons(self):

        for button in self.buttons:
            button.end_button()

        self.buttons = []

    def place_buttons(self):
        self.clean_buttons()

        controls = [["save name", "Click_to_enter_save_name_here.", True], ["save", "Confirm_save.", False],
                    ["cancel", "Go_back_to_builder.", False]]

        positions = [(0, 0), (-0.5, -1.0), (0.5, -1.0)]

        for i in range(len(controls)):
            control_type = controls[i][0]
            text_entry = controls[i][2]

            names = control_type.split()
            label = "\n".join(["{0: ^10}".format(name).upper() for name in names])

            mouse_help = controls[i][1]

            if text_entry:
                button_type = "large_button"
            else:
                button_type = "round_button"

            location = self.option_buttons.worldPosition.copy()
            position = positions[i]

            location.x += position[0] * 1.5
            location.y += position[1] * 0.85

            button = buildutils.Button(self, button_type, control_type, label, location, mouse_over=mouse_help,
                                       text_entry=text_entry)
            if text_entry:
                self.vehicle_name_box = button

            self.buttons.append(button)

    def process_mode(self):
        inherited_process = super().process_mode()

        if inherited_process:
            return inherited_process

        else:

            for button in self.buttons:
                button.update()

            if self.refresh_controls:
                self.refresh_controls = False
                self.place_buttons()

    def mouse_pointer(self):
        mouse_hit = self.mouse_hit_ray("background")
        button_hit = self.mouse_hit_ray("button_click")

        help_text = ""

        if button_hit[0]:
            owner = button_hit[0]["button_owner"]
            if owner.name == "save":
                if self.left_button:

                    in_path = bge.logic.expandPath("//vehicles/saved_vehicles.txt")
                    try:
                        with open(in_path, "r") as infile:
                            vehicle_dict = json.load(infile)
                    except:
                        vehicle_dict = {}

                    save_name = self.vehicle_name_box.text_contents.lower()

                    if vehicle_dict.get(save_name):
                        message_text = self.scene.addObject("text_object", self.option_buttons, 240)
                        message_text.worldPosition.y -= 4.0
                        message_text.localScale *= 0.2
                        message_text["Text"] = "That name is already in_use."
                        message_text.color = [1.0, 0.0, 0.0, 1.0]
                        self.refresh_controls = True

                    else:
                        message_text = self.scene.addObject("text_object", self.option_buttons, 60)
                        message_text.worldPosition.y -= 4.0
                        message_text.localScale *= 0.2
                        message_text["Text"] = "saved."
                        message_text.color = [0.0, 1.0, 0.0, 1.0]

                        vehicle_stats.save_vehicle(vehicle_dict, self.manager.chassis_size, self.manager.turret_size,
                                                   self.manager.contents, save_name)

            elif owner.name == "cancel":
                if self.left_button:
                    self.mode_change = "DebugVehicleBuilder"

            elif owner.name == "save name":
                if self.left_button:
                    owner.clicked = True

            if button_hit[0].get("mouse_over"):
                help_text = button_hit[0]["mouse_over"]

        if help_text:
            self.mouse_text["Text"] = help_text
            longest = sorted(help_text.split("\n"), key=len, reverse=True)[0]

            x_length = len(longest) * 0.14
            y_length = len(help_text.split("\n")) * 0.22
            self.mouse_text_shadow.localScale = [x_length, y_length, 0.0]

        else:
            self.mouse_text["Text"] = ""
            self.mouse_text_shadow.localScale = [0.0, 0.0, 0.0]

        if mouse_hit[0]:
            mouse_position = mouse_hit[1]
            self.mouse.worldPosition = mouse_position
            self.mouse.worldPosition.z = 0.25


class ExitMode(BaseBuilder):
    def __init__(self, manager):
        super().__init__(manager)

        self.background = self.scene.addObject("exit_background", self.own, 0)
        self.background.worldPosition.z -= 0.1

        self.option_buttons = bgeutils.get_ob("option_buttons", self.background.children)

        self.refresh_controls = True
        self.buttons = []

    def clean_up(self):
        super().clean_up()

        self.clean_buttons()

    def clean_buttons(self):

        for button in self.buttons:
            button.end_button()

        self.buttons = []

    def place_buttons(self):

        self.clean_buttons()

        controls = [["really_exit?", "", True], ["yes", "Sure,_exit.", False],
                    ["no", "Go_back_to_builder.", False]]

        location = self.option_buttons.worldPosition.copy()

        for i in range(len(controls)):
            control_type = controls[i][0]
            text_box = controls[i][2]

            names = control_type.split()
            label = "\n".join(["{0: ^10}".format(name).upper() for name in names])

            mouse_help = controls[i][1]

            button = buildutils.Button(self, "round_button", control_type, label, location, mouse_over=mouse_help,
                                       text_box=text_box)
            location.y -= 0.85

            self.buttons.append(button)

    def process_mode(self):
        inherited_process = super().process_mode()

        if inherited_process:
            return inherited_process

        else:

            if self.refresh_controls:
                self.refresh_controls = False
                self.place_buttons()

    def mouse_pointer(self):
        mouse_hit = self.mouse_hit_ray("background")
        button_hit = self.mouse_hit_ray("button_click")

        help_text = ""

        if button_hit[0]:
            owner = button_hit[0]["button_owner"]
            if owner.name == "yes":
                if self.left_button:
                    bge.logic.endGame()

            elif owner.name == "no":
                if self.left_button:
                    self.mode_change = "DebugVehicleBuilder"

            if button_hit[0].get("mouse_over"):
                help_text = button_hit[0]["mouse_over"]

        if help_text:
            self.mouse_text["Text"] = help_text
            longest = sorted(help_text.split("\n"), key=len, reverse=True)[0]

            x_length = len(longest) * 0.14
            y_length = len(help_text.split("\n")) * 0.22
            self.mouse_text_shadow.localScale = [x_length, y_length, 0.0]

        else:
            self.mouse_text["Text"] = ""
            self.mouse_text_shadow.localScale = [0.0, 0.0, 0.0]

        if mouse_hit[0]:
            mouse_position = mouse_hit[1]
            self.mouse.worldPosition = mouse_position
            self.mouse.worldPosition.z = 0.25


class DebugBuilderMode(BaseBuilder):
    def __init__(self, manager):
        super().__init__(manager)

        self.background = self.scene.addObject("builder_background", self.own, 0)
        self.background.worldPosition.z -= 0.1

        self.chassis_buttons = bgeutils.get_ob("chassis_buttons", self.background.children)
        self.parts_buttons = bgeutils.get_ob("parts_buttons", self.background.children)
        self.item_type_buttons = bgeutils.get_ob("item_type_buttons", self.background.children)
        self.option_buttons = bgeutils.get_ob("option_buttons", self.background.children)
        self.part_list_text = bgeutils.get_ob("part_list_text", self.background.children)

        self.info_text = bgeutils.get_ob("info_text", self.background.children)
        self.layout = bgeutils.get_ob("layout", self.background.children)
        self.faction_controls = bgeutils.get_ob("faction_controls", self.background.children)
        self.cammo_buttons = bgeutils.get_ob("cammo_buttons", self.background.children)

        self.model_display = bgeutils.get_ob("model_display", self.background.children)
        self.model_rotation = 0.0

        self.faction_label = vehicle_parts.faction_dict[self.manager.faction]
        self.year = str(1936 + int(self.manager.game_turn * 0.25))
        if self.manager.game_turn == 35:
            self.year += "!"

        self.cammo_dict = vehicle_parts.cammo_dict
        self.cammo = 0

        self.selected_part = None
        self.rotated = False

        self.controls = []
        self.buttons = []
        self.info_buttons = []

        self.tiles = []
        self.vehicle_tiles = []
        self.cursor_display = []

        self.stats = {}

        self.refresh_all = True
        self.refresh_buttons = False
        self.refresh_vehicle = False
        self.refresh_tiles = False

        self.tile_scale = 1.0
        self.item_type = self.manager.selected_parts

        self.vehicle_display = None

    def clean_buttons(self):

        for button in self.buttons:
            button.end_button()

        self.buttons = []

    def place_buttons(self):

        self.clean_buttons()

        self.tech_level_dict = self.get_tech_levels()

        location = self.parts_buttons.worldPosition.copy()

        item_keys = [key for key in self.parts_dict if
                     self.parts_dict[key]["part_type"] == self.item_type and self.parts_dict[key]
                     ["level"] <= self.tech_level_dict.get(self.parts_dict[key]["part_type"], 1)]

        parts = sorted(item_keys, key=lambda my_key: self.parts_dict[my_key]["level"])

        x = 0
        y = 0

        for part_key in parts:
            part = self.parts_dict[part_key]

            button_color = self.color_dict[self.item_type]
            names = part["name"].split()

            label = "\n".join(["{0: ^12}".format(name).upper() for name in names])
            button_location = [location[0] + (x * 1.2), location[1] - (y * 0.9), location[2]]
            button = buildutils.Button(self, "medium_button", "PART", label, button_location, part_key=part_key,
                                       color=button_color, mouse_over="", scale=0.8)

            if x > 4:
                x = 0
                y += 1

            else:
                x += 1

            self.buttons.append(button)

    def clean_controls(self):

        for control in self.controls:
            control.end_button()

        self.controls = []

    def place_controls(self):

        self.clean_controls()

        location = self.chassis_buttons.worldPosition.copy()

        chassis_info = self.chassis_dict[self.chassis_size]
        chassis_name = bgeutils.add_spaces(chassis_info["name"])
        turret_info = self.turret_dict[self.turret_size]
        turret_name = bgeutils.add_spaces(turret_info["name"].upper())

        chassis_controls = [["chassis_smaller", "<<", "small_button", "Set_chassis_size_smaller."],
                            ["chassis_reset", chassis_name, "medium_button", None],
                            ["chassis_larger", ">>", "small_button", "Set_chassis_size_larger."],
                            ["turret_smaller", "<<", "small_button", "Set_turret_size_smaller."],
                            ["turret_reset", turret_name, "medium_button", None],
                            ["turret_larger", ">>", "small_button", "Set_turret_size_larger."]]

        for i in range(len(chassis_controls)):
            details = chassis_controls[i]
            name = details[0]
            label = details[1]
            if label != "<<" and label != ">>":
                names = label.split()
                label = "\n".join(["{0: ^10}".format(name).upper() for name in names])
            else:
                label = "{0: ^4}".format(label)

            button_type = details[2]
            mouse_help = details[3]

            text_box = False
            if not mouse_help:
                text_box = True

            button = buildutils.Button(self, button_type, name, label, location, mouse_over=mouse_help,
                                       text_box=text_box,
                                       scale=0.75)
            location.x += 1.0

            self.controls.append(button)

        self.faction_label = vehicle_parts.faction_dict[self.manager.faction]
        self.year = str(1936 + int(self.manager.game_turn * 0.25))
        if self.manager.game_turn == 48:
            self.year += "!"

        faction_name = "faction: {}".format(self.faction_label)
        game_turn = "turn:_{}".format(self.manager.game_turn)
        year = "year: {}".format(self.year)

        faction_controls = [["faction_less", "<<", "small_button", "Change_faction."],
                            ["faction_name", faction_name, "medium_button", None],
                            ["faction_more", ">>", "small_button", "Change_faction."],
                            ["turn_less", "<<", "small_button", "Change_game_turn."],
                            ["turn", game_turn, "medium_button", None],
                            ["turn_more", ">>", "small_button", "Change_game_turn."],
                            ["year", year, "medium_button", None]]

        location = self.faction_controls.worldPosition.copy()

        for i in range(len(faction_controls)):
            details = faction_controls[i]
            name = details[0]
            label = details[1]
            if label != "<<" and label != ">>":
                names = label.split()
                label = "\n".join(["{0: ^10}".format(name).upper() for name in names])
            else:
                label = "{0: ^4}".format(label)

            button_type = details[2]
            mouse_help = details[3]

            text_box = False
            if not mouse_help:
                text_box = True

            button = buildutils.Button(self, button_type, name, label, location, mouse_over=mouse_help,
                                       text_box=text_box,
                                       scale=0.75)
            location.x += 1.0

            self.controls.append(button)

        location = self.cammo_buttons.worldPosition.copy()

        camo_text = buildutils.Button(self, "round_button", "cam_text_box", "camouflage:", location, mouse_over="",
                                      text_box=True,
                                      scale=0.65)
        self.controls.append(camo_text)
        location.x += 0.5

        for c in range(0, 15):
            cammo = self.cammo_dict[str(c)]

            location.x += 0.35

            cammo_name = "cammo_{}".format(c)
            cammo_label = "{0: ^4}".format(c + 1)
            camo_button = buildutils.Button(self, "white_button", cammo_name, cammo_label, location,
                                            mouse_over="Set_display_camouflage.",
                                            scale=0.45, color=cammo)

            self.controls.append(camo_button)

        location = self.item_type_buttons.worldPosition.copy()

        items = ["engine", "weapon", "suspension", "utility", "armor", "crew", "design"]

        for i in range(len(items)):
            item_type = items[i]
            mouse_help = "select\n{}\nitems.".format(item_type)
            button_color = self.color_dict[item_type]
            label = "{0: ^10}".format(item_type.upper())

            text_box = False
            if item_type == self.item_type:
                text_box = True

            button = buildutils.Button(self, "round_button", item_type, label, location, color=button_color,
                                       mouse_over=mouse_help,
                                       scale=0.85, text_box=text_box)
            location.y -= 0.75

            self.controls.append(button)

        controls = [["check", "Evaluate_design\nperformance."], ["save", "Save_this\ndesign."],
                    ["load", "Load_another\ndesign."], ["exit", "back_to_main\nmenu."]]

        location = self.option_buttons.worldPosition.copy()

        for i in range(len(controls)):
            control_type = controls[i][0]
            label = "{0: ^10}".format(control_type.upper())
            mouse_help = controls[i][1]

            button = buildutils.Button(self, "round_button", control_type, label, location, mouse_over=mouse_help)
            location.y -= 0.85

            self.controls.append(button)

    def clean_vehicle_tiles(self):

        if self.vehicle_display:
            self.vehicle_display.end_vehicle()

        for ob in self.vehicle_tiles:
            ob.endObject()

        self.vehicle_tiles = []

    def redraw_vehicle(self):

        self.clean_vehicle_tiles()

        origin = self.layout.worldPosition.copy()

        items = []

        for content_key in self.contents:
            contents = self.contents[content_key]

            if contents.parent_tile:
                if content_key == contents.parent_tile:
                    if content_key not in items:
                        items.append(contents.parent_tile)

        for item_key in items:

            item = self.contents[item_key]
            part = item.part
            part_type = self.parts_dict[part]["part_type"]
            color = self.color_dict[part_type]

            chassis = self.chassis_dict[self.chassis_size]
            turret = self.turret_dict[self.turret_size]

            max_x = chassis["x"]
            max_y = max(chassis["y"] + 3, chassis["y"] + turret["y"])

            for x in range(-1, max_x + 1):
                for y in range(-1, max_y + 1):
                    offset = mathutils.Vector([(x + 0.5) - (max_x * 0.5), y - (max_y * 0.5), 0.0])
                    offset *= self.tile_scale

                    position = origin.copy() + offset
                    position.z = 0.05

                    search_array = [(1, 0, 1), (1, 1, 2), (0, 1, 4), (0, 0, 8)]

                    tile_number = 0

                    for n in search_array:
                        key = (x + n[0], y + n[1])
                        valid = False

                        n_tile = self.contents.get(key)
                        if n_tile:
                            if n_tile.part:
                                if item.part == n_tile.part:
                                    if n_tile.location == item.location:
                                        valid = True

                        if valid:
                            tile_number += n[2]

                    if tile_number > 0:
                        display_tile = "blank_tile"
                        if part_type == "design":
                            display_tile = "full_tile"

                        tile_name = "{}.{}".format(display_tile, str(tile_number).zfill(3))
                        tile_object = self.scene.addObject(tile_name, self.own, 0)
                        tile_object.worldPosition = position
                        sub_offset = self.tile_scale * 0.5
                        tile_object.worldPosition += mathutils.Vector([sub_offset, sub_offset, 0.0])
                        tile_object.color = color

                        tile_object.localScale *= self.tile_scale
                        self.vehicle_tiles.append(tile_object)

                        if (x, y) == item.parent_tile:
                            try:
                                icon_position = position.copy()
                                icon_position.z += 0.05
                                icon = self.scene.addObject("part_icon_{}".format(part), self.own, 0)

                                x_offset = ((self.parts_dict[part]["x_size"] * 0.5) - 0.5) * self.tile_scale
                                y_offset = ((self.parts_dict[part]["y_size"] * 0.5) - 0.5) * self.tile_scale

                                if item.rotated:
                                    icon_offset = mathutils.Vector([x_offset, y_offset, 0.0])
                                    icon.applyRotation([0.0, 0.0, math.radians(90)])
                                else:
                                    icon_offset = mathutils.Vector([y_offset, x_offset, 0.0])

                                icon_position += icon_offset
                                icon.localScale *= self.tile_scale
                                icon.worldPosition = icon_position
                                self.vehicle_tiles.append(icon)
                            except:
                                pass

        text_origin = self.part_list_text.worldPosition.copy()

        tx = 0
        ty = 0

        exclusive_display = []

        labels = []

        for _ in range(28):
            text_offset = mathutils.Vector([tx, ty * 0.17, 0.0])
            text_position = text_origin.copy() - text_offset
            text_position.z = 0.1

            text = self.scene.addObject("text_object", self.own, 0)
            text["Text"] = ""
            text.localScale *= 0.15
            text.worldPosition = text_position
            self.vehicle_tiles.append(text)

            if ty > 36:
                tx += 6
                ty = 0
            else:
                ty += 3

            labels.append([text, text_position, False])

        for i in range(len(items)):
            if labels:
                location = items[i]
                item = self.contents[location]
                part = item.part
                part_type = self.parts_dict[part]["part_type"]

                part_location = item.location
                name = self.parts_dict[part]["name"]
                color = self.color_dict[part_type]

                single_labels = ["suspension", "armor", "design"]

                if part_type in single_labels:
                    identifier = (part, None)
                else:
                    identifier = (part, part_location)

                if identifier not in exclusive_display:
                    exclusive_display.append(identifier)
                    display_name = "\n".join(name.split()).upper()

                    x, y = location

                    offset = mathutils.Vector([(x + 0.5) - (max_x * 0.5), y - (max_y * 0.5), 0.0])
                    offset *= self.tile_scale

                    position = origin.copy() + offset
                    position.z = 0.1

                    best_label = None
                    closest = 20000.0

                    for t in range(len(labels)):
                        label = labels[t]
                        if not label[2]:
                            label_position = label[1].copy()
                            label_position.x += 0.5

                            target_vector = position.copy() - label_position
                            distance = target_vector.length

                            if distance < closest:
                                closest = distance
                                best_label = t

                    if best_label is not None:
                        labels[best_label][2] = True
                        label = labels[best_label]
                        label_object = label[0]
                        label_position = label[1]

                        label_object["Text"] = display_name
                        label_object.color = color
                        line = self.scene.addObject("feature_line", self.own, 0)
                        line.color = color
                        line.worldPosition = label_position
                        line.worldPosition.z = 0.1

                        target_vector = position.copy() - label_position.copy()
                        line.alignAxisToVect(target_vector, 0, 1.0)
                        line.localScale.x = target_vector.length
                        self.vehicle_tiles.append(line)

        if self.stats:

            if "GUN_CARRIAGE" in self.stats.flags:
                self.vehicle_display = model_display.ArtilleryModel(self.model_display, self.stats, scale=0.30,
                                                                    cammo=self.cammo)

            else:
                self.vehicle_display = model_display.VehicleModel(self.model_display, self.stats, scale=0.30,
                                                                  cammo=self.cammo)

            print("showing")

    def clean_tiles(self):

        for tile in self.tiles:
            tile.endObject()

        self.tiles = []

    def redraw_tiles(self):

        self.clean_tiles()

        origin = self.layout.worldPosition.copy()

        chassis = self.chassis_dict[self.chassis_size]
        turret = self.turret_dict[self.turret_size]

        self.tile_scale = 6.0 / max(chassis["y"] + 3, chassis["y"] + turret["y"])

        tile_types = ["FRONT", "FLANKS", "TURRET", "BLOCKED"]

        max_x = chassis["x"]
        max_y = max(chassis["y"] + 3, chassis["y"] + turret["y"])

        for i in range(len(tile_types)):
            tile_type = tile_types[i]

            if tile_type != "BLOCKED":
                tile_ob = "chassis_tile"
            else:
                tile_ob = "full_tile"

            for x in range(-1, max_x + 1):
                for y in range(-1, max_y + 1):

                    offset = mathutils.Vector([(x + 0.5) - (max_x * 0.5), y - (max_y * 0.5), 0.0])
                    offset *= self.tile_scale

                    position = origin.copy() + offset

                    search_array = [(1, 0, 1), (1, 1, 2), (0, 1, 4), (0, 0, 8)]
                    tile_number = 0

                    for n in search_array:
                        search_key = (x + n[0], y + n[1])

                        n_tile = self.contents.get(search_key)
                        if n_tile:
                            if n_tile.location == tile_type:
                                tile_number += n[2]

                    if i == 0 and tile_type != "BLOCKED":
                        if self.contents.get((x, y)):
                            collision_tile = self.scene.addObject("physical_tile", self.own, 0)
                            collision_tile.worldPosition = position.copy()
                            collision_tile["contents"] = True
                            collision_tile["location"] = (x, y)
                            collision_tile.localScale *= self.tile_scale
                            self.tiles.append(collision_tile)

                    if tile_number > 0:
                        tile_name = "{}.{}".format(tile_ob, str(tile_number).zfill(3))
                        tile_object = self.scene.addObject(tile_name, self.own, 0)
                        tile_object.worldPosition = position.copy()
                        tile_object.color = [0.5, 0.5, 0.5, 1.0]
                        sub_offset = self.tile_scale * 0.5
                        tile_object.worldPosition += mathutils.Vector([sub_offset, sub_offset, 0.0])
                        tile_object.localScale *= self.tile_scale
                        self.tiles.append(tile_object)

    def place_items(self):

        tile_location = None

        if self.left_button or self.right_button:

            hit_object = self.mouse_hit_ray("contents")

            if hit_object[0]:
                tile_location = hit_object[0]["location"]

        if self.contents.get(tile_location):
            tile_contents = self.contents.get(tile_location)
            is_turret = tile_contents.location == "TURRET"
            current_contents = tile_contents.part
            current_location = tile_contents.location
            current_parent = tile_contents.parent_tile

            if self.right_button:
                if current_contents:
                    for tile_key in self.contents:
                        check_tile = self.contents[tile_key]
                        if check_tile.parent_tile == current_parent:
                            check_tile.part = ""
                            check_tile.parent_tile = None
                            check_tile.rotated = False
                    self.refresh_vehicle = True
            else:
                if self.selected_part:
                    selected_part = self.parts_dict[self.selected_part]
                    can_add = True
                    containers = []

                    turret_only = selected_part.get("turret_only")

                    if turret_only == 1 and not is_turret:
                        can_add = False
                    elif turret_only == -1 and is_turret:
                        can_add = False
                    else:
                        if self.rotated:
                            x_max = selected_part["x_size"]
                            y_max = selected_part["y_size"]
                        else:
                            x_max = selected_part["y_size"]
                            y_max = selected_part["x_size"]

                        for x in range(x_max):
                            for y in range(y_max):
                                x_location = x + tile_location[0]
                                y_location = y + tile_location[1]
                                check_location = (x_location, y_location)

                                containers.append(check_location)

                                check_tile = self.contents.get(check_location)
                                if not check_tile:
                                    can_add = False
                                else:
                                    if check_tile.location == "BLOCKED":
                                        can_add = False

                                    if check_tile.location != current_location:
                                        can_add = False

                                    if check_tile.parent_tile:
                                        can_add = False
                                    if check_tile.location == "TURRET" and not is_turret:
                                        can_add = False
                                    if not check_tile.location == "TURRET" and is_turret:
                                        can_add = False

                    if can_add:
                        self.manager.audio.sound_effect("work{}".format(random.randint(1, 8)), self.own,
                                                        attenuation=0.6)

                        for container in containers:
                            self.contents[container].part = self.selected_part
                            self.contents[container].parent_tile = tile_location
                            if self.rotated:
                                self.contents[container].rotated = True

                        self.refresh_vehicle = True

    def clean_cursor(self):

        for ob in self.cursor_display:
            ob.endObject()

        self.cursor_display = []

    def redraw_cursor_display(self):

        self.clean_cursor()

        scale = self.tile_scale

        if self.selected_part:
            selected_part_info = self.parts_dict[self.selected_part]

            if self.rotated:
                x_max = selected_part_info["x_size"]
                y_max = selected_part_info["y_size"]
            else:
                x_max = selected_part_info["y_size"]
                y_max = selected_part_info["x_size"]

            tile_type = selected_part_info["part_type"]
            color = self.color_dict[tile_type]

            icon_tiles = {(x, y): 1 for x in range(x_max) for y in range(y_max)}

            for x in range(-1, x_max):
                for y in range(-1, y_max):

                    search_array = [(1, 0, 1), (1, 1, 2), (0, 1, 4), (0, 0, 8)]

                    tile_number = 0

                    for n in search_array:
                        key = (x + n[0], y + n[1])
                        if icon_tiles.get(key):
                            tile_number += n[2]

                    if tile_number > 0:
                        tile_name = "blank_tile.{}".format(str(tile_number).zfill(3))
                        tile = self.scene.addObject(tile_name, self.mouse, 0)
                        x_position = (x + 0.5) * scale
                        y_position = (y + 0.5) * scale
                        tile.worldPosition += mathutils.Vector([x_position, y_position, -0.05])
                        tile.localScale *= scale
                        tile.setParent(self.mouse)
                        tile.color = color

                        self.cursor_display.append(tile)

    def handle_buttons(self):

        button_hit = self.mouse_hit_ray("button_click")

        if button_hit[0]:
            owner = button_hit[0]["button_owner"]
            if not owner.clicked:
                if owner.name == "PART":
                    if self.right_button:
                        self.manager.audio.sound_effect("select_1", self.own,
                                                        attenuation=0.6)

                        owner.clicked = True
                        self.selected_part = None
                        self.redraw_cursor_display()

                    if self.left_button:
                        self.manager.audio.sound_effect("select_2", self.own,
                                                        attenuation=0.6)
                        owner.clicked = True
                        self.selected_part = owner.part_key
                        self.redraw_cursor_display()

                elif owner.name == "exit":

                    if self.left_button:
                        self.manager.audio.sound_effect("select_2", self.own,
                                                        attenuation=0.6)
                        self.preserve_contents()
                        self.mode_change = "VehicleExit"

                elif owner.name == "save":
                    if self.left_button:
                        self.preserve_contents()
                        self.mode_change = "VehicleSave"

                elif owner.name == "check":
                    pass
                    # do check

                else:
                    if self.left_button:
                        self.manager.audio.sound_effect("select_2", self.own,
                                                        attenuation=0.6)
                        owner.clicked = True

                        items = ["engine", "weapon", "suspension", "utility", "armor", "crew", "design"]
                        if owner.name in items:
                            self.item_type = owner.name
                            self.refresh_all = True
                            # self.refresh_buttons = True

                        if owner.name == "chassis_smaller":
                            self.chassis_size = max(1, self.chassis_size - 1)
                            self.turret_size = min(self.turret_size, self.chassis_size + 1)
                            self.contents = []
                            self.refresh_all = True
                        elif owner.name == "chassis_larger":
                            self.chassis_size = min(4, self.chassis_size + 1)
                            self.turret_size = min(self.turret_size, self.chassis_size + 1)
                            self.contents = []
                            self.refresh_all = True
                        elif owner.name == "turret_smaller":
                            self.turret_size = max(0, self.turret_size - 1)
                            self.contents = []
                            self.refresh_all = True
                        elif owner.name == "turret_larger":
                            self.turret_size = min(self.chassis_size + 1, self.turret_size + 1)
                            self.contents = []
                            self.refresh_all = True

                        elif owner.name == "turn_more":
                            self.manager.game_turn = min(52, self.manager.game_turn + 1)
                            self.contents = []
                            self.refresh_all = True

                        elif owner.name == "turn_less":
                            self.manager.game_turn = max(1, self.manager.game_turn - 1)
                            self.contents = []
                            self.refresh_all = True

                        elif owner.name == "faction_less":
                            self.manager.faction = max(1, self.manager.faction - 1)
                            self.contents = []
                            self.refresh_all = True

                        elif owner.name == "faction_more":
                            self.manager.faction = min(6, self.manager.faction + 1)
                            self.contents = []
                            self.refresh_all = True

                        else:
                            if "cammo" in owner.name:
                                name = owner.name.split("_")
                                self.cammo = int(name[1])
                                self.refresh_vehicle = True

                    self.redraw_cursor_display()

        else:
            contents_hit = self.mouse_hit_ray("contents")
            if not contents_hit[0]:
                if self.right_button:
                    self.rotated = not self.rotated
                    self.redraw_cursor_display()

    def clean_info_buttons(self):

        for button in self.info_buttons:
            button.end_button()

        self.info_buttons = []

    def generate_stats(self):

        self.clean_info_buttons()
        self.stats = vehicle_stats.VehicleStats(self.chassis_size, self.turret_size, self.contents, self.manager.faction)

        # stat_1_categories = ["tons", "cost", "stability", "total_crew", "suspension_type", "suspension_rating",
        #                      "engine_rating"]
        # stat_1_string = ""
        #
        # for category in stat_1_categories:
        #     entry = self.vehicle_stats[category]
        #     try:
        #         entry = round(entry, 1)
        #     except:
        #         entry = entry
        #
        #     if category == "suspension_type":
        #         stat_1_string = "{}{:<18}\n{:>21}\n".format(stat_1_string, category + ":", str(entry))
        #     else:
        #         stat_1_string = "{}{:<18}{:>3}\n".format(stat_1_string, category + ":", str(entry))
        #
        # stat_2_categories = ["on_road_handling", "off_road_handling", "on_road", "off_road", "fuel", "stores",
        #                      "vision_distance"]
        # stat_2_string = ""
        #
        # for category in stat_2_categories:
        #     entry = self.vehicle_stats[category]
        #     try:
        #         entry = round(entry, 1)
        #     except:
        #         entry = entry
        #
        #     stat_2_string = "{}{:<18}{:>3}\n".format(stat_2_string, category + ":", entry)
        #
        # ### armor display
        #
        # if self.turret_size:
        #     locations = ["FRONT", "FLANKS", "TURRET"]
        # else:
        #     locations = ["FRONT", "FLANKS"]
        #
        # armor_string = "{:>21}".format("CP_-_HP_-_AP:")
        # crit_string = ""
        #
        # for location in locations:
        #     current_section = self.vehicle_stats["sections"][location]
        #
        #     if self.vehicle_stats["armored"]:
        #         armor_rating = str(int(current_section["rating"])).zfill(2)
        #     else:
        #         armor_rating = "-"
        #
        #     max_warning = ""
        #     if current_section["rating"] == current_section["max"]:
        #         max_warning = "*"
        #
        #     components = [str(int(current_section["manpower"])).zfill(2),
        #                   str(int(current_section["durability"])).zfill(2),
        #                   armor_rating, max_warning]
        #
        #     hp_string = "{:<8}{} - {} - {}{}".format(location + ":", *components)
        #     armor_string = "{}\n{}".format(armor_string, hp_string)
        #
        #     added_crits = []
        #     for crit_entry in self.vehicle_stats["sections"][location]["crits"]:
        #         if crit_entry[:1] not in added_crits and crit_entry != "CHASSIS":
        #             added_crits.append(crit_entry[:1])
        #
        #     crits = "/".join(added_crits)
        #     crit_string = "{}\n{}{}".format(crit_string, location + "_CRITS:_", crits)

        label = "" #bgeutils.add_spaces("".join([stat_1_string, stat_2_string, armor_string, crit_string]))
        help_lines = ["Vehicle_statistics:", "Suspension_rating_should_exceed_tonnage.",
                      "Each_engine_or_armor_section_above_1_adds", "only_50_percent_to_rating.",
                      "CP=_Crew_points,_affects_reload_speed",
                      "HP=_Durability", "AP=_Armor_points",
                      "CRITICAL_LOCATIONS=",
                      "D=_drive,_W=_weapon,_C=_crew,_E=_engine",
                      "Crew_type_sections_weigh_50_percent.",
                      "Armor_sections_weigh_more_or_less_depending",
                      "on_the_chassis_and_turret_size."]

        mouse_help = bgeutils.add_spaces("\n".join(help_lines))
        location = self.info_text.worldPosition.copy()

        button = buildutils.Button(self, "large_text_box", "stat", label, location, mouse_over=mouse_help,
                                   text_box=True,
                                   scale=1.0)
        self.info_buttons.append(button)

    def regenerate_chassis(self):

        self.contents = {}

        chassis = self.chassis_dict[self.chassis_size]
        turret = self.turret_dict[self.turret_size]

        blocked_tiles = []

        block_padding_x = int((chassis["x"] - turret["block_x"]) * 0.5)
        block_padding_y = chassis["front"]

        for x in range(block_padding_x, block_padding_x + turret["block_x"]):
            for y in range(block_padding_y, block_padding_y + turret["block_y"]):
                blocked_tiles.append((x, y))

        for x in range(chassis["x"]):
            for y in range(chassis["y"]):
                chassis_key = (x, y)

                if chassis_key in blocked_tiles:
                    location = "BLOCKED"

                elif y > chassis["front"]:
                    location = "FRONT"

                else:
                    location = "FLANKS"

                weapon_location = location

                if location == "FLANKS":
                    if y < 1:
                        weapon_location = "BACK"
                    elif x >= (chassis["x"] * 0.5):
                        weapon_location = "RIGHT"
                    else:
                        weapon_location = "LEFT"

                self.contents[chassis_key] = vehicle_stats.VehicleTile(x, y, location, weapon_location)

        turret_padding_x = int((chassis["x"] - (turret["x"])) * 0.5)
        turret_padding_y = int(chassis["y"]) + 1

        for x in range(turret_padding_x, turret_padding_x + turret["x"]):
            for y in range(turret_padding_y, turret_padding_y + turret["y"]):
                self.contents[(x, y)] = vehicle_stats.VehicleTile(x, y, "TURRET", "TURRET")

    def mouse_pointer(self):
        mouse_hit = self.mouse_hit_ray("background")
        button_hit = self.mouse_hit_ray("button_click")
        contents_hit = self.mouse_hit_ray("contents")

        help_text = ""

        if button_hit[0]:
            owner = button_hit[0]["button_owner"]
            if owner.name == "PART":
                part = self.parts_dict[owner.part_key]
                help_text = self.part_description(part)

            if button_hit[0].get("mouse_over"):
                help_text = button_hit[0]["mouse_over"]

        elif contents_hit[0]:
            location_key = contents_hit[0]["location"]
            contents = self.contents.get(location_key)

            if contents:
                part_key = contents.part

                if part_key:
                    part = self.parts_dict[part_key]
                    help_text = "{}\n{}\n{}".format(help_text, part["name"].upper(), self.part_description(part))
                elif contents.location == "BLOCKED":
                    help_text = "Occupied_by_turret."
                else:

                    if contents.location != contents.weapon_location:
                        help_text = "vehicle_{}({}).".format(contents.location.lower(),
                                                             contents.weapon_location).upper()
                    else:
                        help_text = "vehicle_{}.".format(contents.location.lower()).upper()

        if help_text:
            help_text = bgeutils.add_spaces(help_text)

            self.mouse_text["Text"] = help_text
            longest = sorted(help_text.split("\n"), key=len, reverse=True)[0]

            x_length = len(longest) * 0.14
            y_length = len(help_text.split("\n")) * 0.22
            self.mouse_text_shadow.localScale = [x_length, y_length, 0.0]

        else:
            self.mouse_text["Text"] = ""
            self.mouse_text_shadow.localScale = [0.0, 0.0, 0.0]

        if mouse_hit[0]:
            mouse_position = mouse_hit[1]
            self.mouse.worldPosition = mouse_position
            self.mouse.worldPosition.z = 0.25

    def clean_up(self):
        super().clean_up()

        self.clean_info_buttons()
        self.clean_buttons()
        self.clean_controls()
        self.clean_vehicle_tiles()
        self.clean_tiles()
        self.clean_cursor()
        self.manager.selected_parts = self.item_type

    def model_display_update(self):

        if self.model_rotation < 1.0:
            self.model_rotation += 0.001
        else:
            self.model_rotation = 0.0

        if self.vehicle_display:
            self.vehicle_display.preview_update(self.model_rotation)

    def process_mode(self):
        inherited_process = super().process_mode()

        if inherited_process:
            return inherited_process

        else:

            self.input.update()
            self.mouse_pointer()

            self.place_items()
            self.handle_buttons()

            if self.refresh_all:
                self.refresh_all = False

                self.selected_part = None
                self.redraw_cursor_display()

                if not self.contents:
                    self.regenerate_chassis()

                self.place_controls()
                self.refresh_tiles = True
                self.refresh_vehicle = True
                self.refresh_buttons = True

            if self.refresh_buttons:
                self.refresh_buttons = False
                self.place_buttons()

            if self.refresh_tiles:
                self.refresh_tiles = False
                self.redraw_tiles()

            if self.refresh_vehicle:
                self.refresh_vehicle = False
                self.generate_stats()
                self.redraw_vehicle()

            for control in self.controls:
                control.update()

            for button in self.buttons:
                button.update()

            self.model_display_update()
