import bge
import mathutils
import math
import json


##############################
### utilities

def split_string_in_lines(contents, line_length):
    words = contents.split()

    new_contents = ""

    word_count = 0

    for word in words:
        if word_count != 0:
            new_contents = "{} ".format(new_contents)

        new_contents = "{}{}".format(new_contents, word)

        if word_count >= line_length:
            new_contents = "{}\n".format(new_contents)
            word_count = 0
        else:
            word_count += 1

    return new_contents


class Tile(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

        self.part = ""
        self.location = None
        self.parent_tile = None
        self.rotated = False


class Button(object):
    def __init__(self, manager, obj_string, name, location, scale):
        self.manager = manager
        self.name = name

        self.obj_string = obj_string
        object_name = "{}_off".format(self.obj_string)

        self.object_box = self.manager.scene.addObject(object_name, self.manager.own, 0)
        self.object_box['button_click'] = True
        self.object_box['button_owner'] = self
        self.object_box.worldPosition = location
        self.text_object = self.manager.scene.addObject("text_object", self.object_box, 0)

        if obj_string == "big_button":
            self.text_object.worldPosition.x -= 1.2
        elif obj_string == "fat_button":
            self.text_object.worldPosition.x -= 1.2
            self.text_object.worldPosition.y += 0.4

        else:
            self.text_object.worldPosition.x -= 0.6

        self.text_object.localScale *= 0.38
        self.text_object.setParent(self.object_box)
        self.text_object.resolution = 8

        self.object_box.localScale *= scale

        self.clicked = False
        self.redrawn = False
        self.click_timer = 0

    def update(self):
        if self.clicked:
            if self.click_timer > 12:
                self.object_box.replaceMesh("{}_off".format(self.obj_string))
                self.clicked = False
                self.redrawn = False
                self.click_timer = 0
            else:
                if not self.redrawn:
                    self.object_box.replaceMesh("{}_on".format(self.obj_string))
                    self.redrawn = True
                self.click_timer += 1


                ##############################


### main loop class

class MainLoop(object):
    def __init__(self, own):

        self.own = own
        self.scene = own.scene
        self.camera = own.scene.active_camera

        bge.logic.mouse.position = (0.5, 0.5)

        self.cursor = [ob for ob in self.scene.objects if ob.get("cursor")][0]

        self.origin = mathutils.Vector([-4.5, -1.2, 0.0])
        self.chassis_size = 1
        self.turret_size = 1

        self.parts_dict = vehicle_parts.get_parts()
        self.chassis_dict = vehicle_parts.get_chassis_dict()
        self.turret_dict = vehicle_parts.get_turret_dict()
        self.suspension_dict = vehicle_parts.get_suspension_dict()

        self.color_dict = {"engine_icon": [0.1, 0.2, 0.1, 1.0],
                           "suspension_icon": [0.05, 0.1, 0.3, 1.0],
                           "utility_icon": [0.3, 0.1, 0.01, 1.0],
                           "mechanical_icon": [0.01, 0.2, 0.15, 1.0],
                           "armor_icon": [0.15, 0.15, 0.01, 1.0],
                           "weapon_icon": [0.2, 0.05, 0.07, 1.0],
                           "empty_icon": [1.0, 0.95, 0.75, 1.0]}

        self.tank_parts = {}
        self.tank_stats = {}
        self.tank_stats_text = self.scene.addObject("text_object", self.own, 0)
        self.tank_stats_text.worldPosition = [-1.5, 2.5, 0.1]
        self.tank_stats_text.localScale *= 0.13
        self.tank_stats_text.color = [0.0, 0.0, 0.0, 1.0]

        self.add_buttons()

        self.tile_objects = []
        self.tile_scale = 1.0

        self.item_button_objects = []

        self.item_types = "engine"

        self.create_vehicle()
        self.do_redraw_vehicle()
        self.redraw_item_buttons()

        self.selected_part = None
        self.part_info_text = None
        self.rotated = False

        self.cursor_display = []

        self.save_name_text = self.scene.addObject("text_object", self.own, 0)
        self.save_name_text.worldPosition = [-4.5, -2.5, 0.1]
        self.save_name_text.localScale *= 0.18
        self.save_name_text.color = [0.0, 0.0, 0.0, 1.0]

        self.save_name_text_content = "generic_vehicle"

    def set_cursor(self):
        mouse_position = bge.logic.mouse.position

        screen_vect = self.camera.getScreenVect(*mouse_position)
        screen_vect.length = 39.0

        target_position = self.camera.worldPosition.copy() - screen_vect

        self.cursor.worldPosition = target_position

    def redraw_cursor_display(self):

        for ob in self.cursor_display:
            ob.endObject()

        self.cursor_display = []

        scale = self.tile_scale

        if self.selected_part:
            selected_part_info = self.parts_dict[self.selected_part]

            if self.rotated:
                x_max = selected_part_info['x_size']
                y_max = selected_part_info['y_size']
            else:
                x_max = selected_part_info['y_size']
                y_max = selected_part_info['x_size']

            tile_type = "{}_icon".format(selected_part_info['type'])
            color = self.color_dict[tile_type]

            icon_tiles = {(x, y): 1 for x in range(x_max) for y in range(y_max)}

            for x in range(-1, x_max):
                for y in range(-1, y_max):

                    search_array = [(1, 0, 1), (1, 1, 2), (0, 1, 4), (0, 0, 8)]

                    tile_number = 1

                    for n in search_array:
                        key = (x + n[0], y + n[1])
                        if icon_tiles.get(key):
                            tile_number += n[2]

                    if selected_part_info['type'] == "armor":
                        tile_name = "armor_component.{}".format(str(tile_number).zfill(3))
                    else:
                        tile_name = "tile_component.{}".format(str(tile_number).zfill(3))

                    tile = self.scene.addObject(tile_name, self.cursor, 0)
                    x_position = (x + 0.5) * scale
                    y_position = (y + 0.5) * scale
                    tile.worldPosition += mathutils.Vector([x_position, y_position, -0.1])
                    tile.localScale *= scale
                    tile.setParent(self.cursor)
                    tile.color = color

                    self.cursor_display.append(tile)

    def mouse_controls(self):

        self.vehicle_over = self.mouse_hit_ray("contents")
        self.button_over = self.mouse_hit_ray("button_click")

        self.left_button = self.mouse_triggered(bge.events.LEFTMOUSE)
        self.right_button = self.mouse_triggered(bge.events.RIGHTMOUSE)
        self.shift_held = self.check_shift_held()

    def mouse_hit_ray(self, property):
        camera = self.camera
        mouse_position = bge.logic.mouse.position
        screen_vect = camera.getScreenVect(*mouse_position)
        target_position = camera.worldPosition - screen_vect
        target_ray = camera.rayCast(target_position, camera, 300.0, property, 0, 1, 0)

        if target_ray[0]:
            return target_ray[0]

        return None

    def mouse_triggered(self, button):
        mouse = bge.logic.mouse

        if mouse.events[button] == bge.logic.KX_INPUT_JUST_ACTIVATED:
            return True

        return False

    def check_shift_held(self):
        triggered = [1, 2]

        if 129 in bge.logic.keyboard.events:
            if bge.logic.keyboard.events[129] in triggered:
                return True

        return False

    def press_buttons(self):

        redraw_contents = False
        redraw_items = False
        redraw_selected = False

        if self.button_over:

            button = self.button_over['button_owner']

            if not button.clicked:

                if button.name == "save":
                    if self.left_button:
                        self.tank_stats['name'] = self.save_name_text_content

                        save_name = "{}{}.txt".format(bge.logic.expandPath("//"), self.save_name_text_content)

                        with open(save_name, "w") as f:
                            json.dump(self.tank_stats, f)

                        button.clicked = True
                        redraw_contents = True

                        button_text = "saved"

                if button.name == 'chassis':

                    if self.left_button:
                        redraw_contents = True
                        button.clicked = True

                        if self.chassis_size < 5:
                            self.chassis_size += 1
                        else:
                            self.chassis_size = 1
                    elif self.right_button:
                        redraw_contents = True
                        button.clicked = True
                        if self.chassis_size > 1:
                            self.chassis_size -= 1
                        else:
                            self.chassis_size = 5

                    if self.turret_size > self.chassis_size + 1:
                        self.turret_size = self.chassis_size + 1
                        turret_button = [b for b in self.buttons if b.name == "turret"][0]
                        turret_button.text_object['Text'] = "\n".join(
                            self.turret_dict[str(self.turret_size)]['name'].split())

                    button_text = "\n".join(self.chassis_dict[str(self.chassis_size)]['name'].split())

                if button.name == 'turret':

                    if self.left_button:
                        redraw_contents = True
                        button.clicked = True

                        if self.turret_size < 6:
                            self.turret_size += 1
                        else:
                            self.turret_size = 0

                    elif self.right_button:
                        redraw_contents = True
                        button.clicked = True
                        if self.turret_size > 0:
                            self.turret_size -= 1
                        else:
                            self.turret_size = 6

                    if self.turret_size > self.chassis_size + 1:
                        self.turret_size = self.chassis_size + 1

                    button_text = "\n".join(self.turret_dict[str(self.turret_size)]['name'].split())

                items = ["engine", "weapon", "suspension", "utility", "armor", "mechanical"]
                if button.name in items:
                    if self.left_button:
                        redraw_items = True
                        button.clicked = True
                        self.item_types = button.name

                if button in self.item_button_objects:
                    if self.left_button:
                        button.clicked = True
                        self.selected_part = button.name
                        redraw_selected = True

        if redraw_contents:
            button.text_object['Text'] = button_text
            self.create_vehicle()
            self.do_redraw_vehicle()
            self.selected_part = None
            self.redraw_selected()

        if redraw_items:
            self.redraw_item_buttons()
            self.selected_part = None
            self.redraw_selected()

        if redraw_selected:
            self.redraw_selected()

        for button in self.buttons:
            button.update()

        for item_button in self.item_button_objects:
            item_button.update()

    def item_text_string(self):

        selected_part_info = self.parts_dict[self.selected_part]

        if selected_part_info['type'] == "engine":
            headings = [["name", "", ""], ["weight", "MASS:", "t"], ["rating", "POWER:", "hp"],
                        ["cost", "COST PER TILE:", ""], ["durability", "DURABILITY:", " points"],
                        ["description", "", ""]]
        elif selected_part_info['type'] == "suspension":
            headings = [["name", "", ""], ["weight", "MASS:", "t"], ["rating", "SUPPORT:", "t"],
                        ["cost", "COST PER TILE:", ""], ["durability", "DURABILITY:", " points"],
                        ["stability", "STABILITY:", " pts"], ["firm", "ROAD RADIO:", ""],
                        ["soft", "OFF ROAD RATIO:", ""], ["description", "", ""]]
        elif selected_part_info['type'] == "armor":
            headings = [["name", "", ""], ["weight", "MASS:", "t"], ["rating", "POINTS PER TILE:", ""],
                        ["range", "MAX EFFECTIVENESS:", "pts"], ["cost", "COST PER TILE:", ""],
                        ["durability", "DURABILITY:", " points"], ["description", "", ""]]
        elif selected_part_info['type'] == "utility" or selected_part_info['type'] == "mechanical":
            headings = [["name", "", ""], ["weight", "MASS:", "t"], ["cost", "COST PER TILE:", ""],
                        ["durability", "DURABILITY:", " points"], ["description", "", ""]]
        elif selected_part_info['type'] == "weapon":
            headings = [["name", "", ""], ["weight", "MASS:", "t"], ["rating", "PENETRATION:", " pts"],
                        ["range", "RANGE:", " tiles"], ["damage", "DAMAGE:", ""], ["stability", "ACCURACY:", ""],
                        ["rate_of_fire", "RELOAD TIME:", ""], ["weight", "MASS:", "t"], ["cost", "COST PER TILE:", ""],
                        ["durability", "DURABILITY:", " points"], ["description", "", ""]]

        else:
            return ""

        contents = ["{}{}{}".format(heading[1], selected_part_info[heading[0]], heading[2]) for heading in headings if
                    selected_part_info.get(heading[0])]

        contents[0] = contents[0].upper()
        contents[-1] = split_string_in_lines(contents[-1], 6)

        content_string = ""
        content_count = 0

        for i in range(len(contents)):
            content = contents[i]

            if i == 1 or i == len(contents) - 1:
                content_string = "{}\n\n".format(content_string)

            elif content_count != 0:
                content_string = "{}    ".format(content_string)

            content_string = "{}{}".format(content_string, content)
            if content_count > 1:
                content_string = "{}\n".format(content_string)
                content_count = 0
            else:
                content_count += 1

        if selected_part_info.get("flags") == "low_velocity":
            content_string = "{}\nNOTE: reduced penetration at long range.".format(content_string)

        if selected_part_info.get("turret_only") == 1:
            content_string = "{}\nNOTE: Can be fitted to turret only.".format(content_string)

        elif selected_part_info.get("turret_only") == -1:
            content_string = "{}\nNOTE: May not be fitted to turret.".format(content_string)

        return content_string

    def redraw_selected(self):

        if self.part_info_text:
            self.part_info_text.endObject()

        if not self.selected_part:
            self.part_info_text = None

        else:
            self.part_info_text = self.scene.addObject("text_object", self.own, 0)
            self.part_info_text.worldPosition = [0.5, -1.1, 0.1]
            self.part_info_text.localScale *= 0.15
            self.part_info_text.color = [0.0, 0.0, 0.0, 1.0]

            self.part_info_text['Text'] = self.item_text_string()

        self.redraw_cursor_display()

    def add_buttons(self):

        save_button = Button(self, "big_button", "save", mathutils.Vector([-1.5, -2.5, 0.1]), 0.4)
        save_button.text_object['Text'] = "save"

        chassis_button = Button(self, "big_button", "chassis", mathutils.Vector([-4.5, 2.5, 0.1]), 0.4)
        chassis_button.text_object['Text'] = "\n".join(self.chassis_dict[str(self.chassis_size)]['name'].split())
        chassis_button.text_object.localPosition.y += 0.15
        chassis_button.text_object.localScale *= 0.8

        turret_button = Button(self, "big_button", "turret", mathutils.Vector([-3.0, 2.5, 0.1]), 0.4)
        turret_button.text_object['Text'] = "\n".join(self.turret_dict[str(self.turret_size)]['name'].split())
        turret_button.text_object.localPosition.y += 0.15
        turret_button.text_object.localScale *= 0.8

        self.buttons = [chassis_button, turret_button]

        items = ["engine", "weapon", "suspension", "utility", "armor", "mechanical"]

        item_start = mathutils.Vector([0.5, 2.5, 0.1])
        offset = mathutils.Vector([0.0, -0.25, 0.0])

        for i in range(6):
            item = items[i]
            location = item_start + (offset * i)
            button = Button(self, "big_button", item, location, 0.2)

            color = mathutils.Vector(self.color_dict["{}_icon".format(item)])
            button.object_box.color = color
            button.text_object.color = color * 2.0
            button.text_object['Text'] = item

            self.buttons.append(button)

    def redraw_item_buttons(self):
        for button in self.item_button_objects:
            button.object_box.endObject()
            button.object_box = None

        self.item_button_objects = []

        item_start = mathutils.Vector([1.5, 2.5, 0.1])
        color = mathutils.Vector(self.color_dict["{}_icon".format(self.item_types)])

        x = 0
        y = 0

        item_keys = [key for key in self.parts_dict if self.parts_dict[key]['type'] == self.item_types]

        item_keys = sorted(item_keys, key=lambda my_key: self.parts_dict[my_key]['weight'])

        for i in range(len(item_keys)):

            item_key = item_keys[i]
            item = self.parts_dict[item_key]
            location = item_start.copy()
            location.x += x * 0.8
            location.y += y * 0.5

            item_button = Button(self, "fat_button", item_key, location, 0.2)

            item_button.object_box.color = color
            item_button.text_object.color = color * 2.0

            name_string = "\n".join(item['name'].split())
            size_string = "{}x{}".format(item['x_size'], item['y_size'])

            item_button.text_object['Text'] = "{}\n{}".format(name_string, size_string)

            if x > 3:
                y -= 1
                x = 0
            else:
                x += 1

            self.item_button_objects.append(item_button)

    def do_redraw_vehicle(self):

        for ob in self.tile_objects:
            ob.endObject()
        self.tile_objects = []

        self.draw_chassis()
        self.generate_stats()

        items = []

        for content_key in self.contents:
            contents = self.contents[content_key]

            if contents.parent_tile:
                if contents.parent_tile not in items:
                    items.append(content_key)

        for item_key in items:

            item = self.contents[item_key]
            part = self.parts_dict[item.part]
            tile_parent = self.contents[item.parent_tile]

            min_x = item_key[0] - 1
            min_y = item_key[1] - 1

            max_size = max(part['x_size'], part['y_size'])

            max_x = item_key[0] + max_size + 1
            max_y = item_key[1] + max_size + 1

            type = part['type']

            for x in range(min_x, max_x):
                for y in range(min_y, max_y):
                    offset = mathutils.Vector([x + 0.5, y + 0.5, 0.0])
                    offset *= self.tile_scale

                    location = self.origin + offset
                    location.z = 0.2

                    search_array = [(1, 0, 1), (1, 1, 2), (0, 1, 4), (0, 0, 8)]

                    tile_number = 1

                    for n in search_array:
                        key = (x + n[0], y + n[1])
                        valid = False

                        n_tile = self.contents.get(key)
                        if n_tile:
                            tile_part = self.parts_dict.get(n_tile.part)

                            if tile_part:
                                if tile_parent == self.contents[n_tile.parent_tile]:
                                    valid = True

                                if item.part == n_tile.part:
                                    if n_tile.location == item.location:
                                        valid = True

                        if valid:
                            tile_number += n[2]

                    if type == "armor":
                        tile_name = "armor_component.{}".format(str(tile_number).zfill(3))
                    else:
                        tile_name = "tile_component.{}".format(str(tile_number).zfill(3))

                    color_key = "{}_icon".format(type)
                    color = mathutils.Vector(self.color_dict[color_key])

                    if tile_number > 1:
                        tile_object = self.scene.addObject(tile_name, self.own, 0)
                        tile_object.worldPosition = location
                        tile_object.color = color

                        if (x, y) == item.parent_tile:
                            label = self.scene.addObject("text_object", tile_object, 0)
                            text = part['short_name'].upper().split(" ", 1)

                            label.localScale *= 0.4
                            label['Text'] = "\n".join(text)
                            label.color = color * 3.0
                            label.color[3] = 1.0

                            if not item.rotated:
                                neg_y = mathutils.Vector([-1.0, 0.0, 0.0])
                                target_rotation = neg_y.to_track_quat("Y", "Z")
                                label.worldPosition += mathutils.Vector([-0.35, -0.61, 0.01])
                                if len(text) > 1:
                                    label.worldPosition += mathutils.Vector([-0.18, -0.0, 0.0])

                                label.worldOrientation = target_rotation
                            else:
                                label.worldPosition += mathutils.Vector([-0.65, -0.7, 0.01])
                                if len(text) > 1:
                                    label.worldPosition += mathutils.Vector([-0.0, 0.3, 0.0])

                            label.setParent(tile_object)

                        tile_object.localScale *= self.tile_scale
                        self.tile_objects.append(tile_object)

    def draw_chassis(self):

        chassis = self.chassis_dict[str(self.chassis_size)]
        turret = self.turret_dict[str(self.turret_size)]

        self.tile_scale = 2.0 / chassis['y']

        types = ["FRONT", "LEFT", "RIGHT", "BACK", "TURRET", "BLOCKED"]

        for i in range(len(types)):
            type = types[i]

            for x in range(-1, chassis["x"]):
                for y in range(-1, chassis["y"] + turret["y"] + 1):
                    offset = mathutils.Vector([x, y, 0.0])
                    offset *= self.tile_scale

                    location = self.origin + offset
                    location.z = 0.0

                    search_array = [(1, 0, 1), (1, 1, 2), (0, 1, 4), (0, 0, 8)]

                    tile_number = 1

                    for n in search_array:
                        key = (x + n[0], y + n[1])
                        valid = False

                        n_tile = self.contents.get(key)
                        if n_tile:
                            if n_tile.location == type:
                                valid = True

                        if valid:
                            tile_number += n[2]

                    tile_name = "empty_component.{}".format(str(tile_number).zfill(3))
                    if type == "BLOCKED":
                        color = [0.2, 0.19, 0.15, 1.0]
                    else:
                        color = [0.6, 0.58, 0.52, 1.0]

                    if tile_number > 1:
                        collision_tile = self.scene.addObject("collision_tile", self.own, 0)
                        collision_tile.worldPosition = location
                        collision_tile['contents'] = True
                        collision_tile['location'] = (x, y)

                        tile_object = self.scene.addObject(tile_name, collision_tile, 0)
                        tile_object.worldPosition += mathutils.Vector([0.5, 0.5, 0.0])
                        tile_object.color = color
                        tile_object.setParent(collision_tile)
                        collision_tile.localScale *= self.tile_scale
                        self.tile_objects.append(collision_tile)

    def place_items(self):

        tile_location = None

        if self.left_button or self.right_button:

            hit_object = self.mouse_hit_ray("contents")

            if hit_object:
                tile_location = hit_object['location']

            elif self.right_button:
                if self.rotated:
                    self.rotated = False
                else:
                    self.rotated = True
                self.redraw_selected()

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
                    self.do_redraw_vehicle()

            else:
                if self.selected_part:
                    selected_part = self.parts_dict[self.selected_part]
                    can_add = True
                    containers = []

                    turret_only = selected_part.get('turret_only')

                    if turret_only == 1 and not is_turret:
                        can_add = False
                    elif turret_only == -1 and is_turret:
                        can_add = False
                    else:
                        if self.rotated:
                            x_max = selected_part['x_size']
                            y_max = selected_part['y_size']
                        else:
                            x_max = selected_part['y_size']
                            y_max = selected_part['x_size']

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
                        for container in containers:
                            self.contents[container].part = self.selected_part
                            self.contents[container].parent_tile = tile_location
                            if self.rotated:
                                self.contents[container].rotated = True

                        self.do_redraw_vehicle()

    def create_vehicle(self):
        chassis = self.chassis_dict[str(self.chassis_size)]
        turret = self.turret_dict[str(self.turret_size)]

        self.contents = {}

        for x in range(chassis["x"]):
            for y in range(chassis["y"]):
                key = (x, y)
                self.contents[key] = Tile(x, y)

                if y < chassis["back"]:
                    self.contents[key].location = "BACK"

                elif y > chassis["front"]:
                    self.contents[key].location = "FRONT"

                else:
                    if x >= chassis["x"] * 0.5:
                        self.contents[key].location = "RIGHT"
                    else:
                        self.contents[key].location = "LEFT"

        block_padding_x = int((chassis["x"] - (turret["block_x"])) * 0.5)
        block_padding_y = chassis["front"]

        for x in range(block_padding_x, block_padding_x + turret["block_x"]):
            for y in range(block_padding_y, block_padding_y + turret["block_y"]):
                key = (x, y)
                self.contents[key].location = "BLOCKED"

        turret_padding_x = int((chassis["x"] - (turret["x"])) * 0.5)
        turret_padding_y = int(chassis["y"]) + 1

        for x in range(turret_padding_x, turret_padding_x + turret["x"]):
            for y in range(turret_padding_y, turret_padding_y + turret["y"]):
                key = (x, y)
                self.contents[key] = Tile(x, y)
                self.contents[key].location = "TURRET"

    def generate_stats(self):

        chassis = self.chassis_dict[str(self.chassis_size)]
        turret = self.turret_dict[str(self.turret_size)]

        self.tank_parts = {}

        for content_key in self.contents:
            contents = self.contents[content_key]

            if contents.parent_tile:
                if contents.parent_tile not in self.tank_parts:
                    self.tank_parts[contents.parent_tile] = {"part": self.contents[contents.parent_tile].part,
                                                             "location": contents.location}

                    ### armor

        special_effects = []
        tons = turret['block_x'] * turret['block_y']
        engine_rating = 0

        fuel_type = None

        suspension = 0
        suspension_type = None

        cost = 0

        stability = 0

        section_dict = {
            "TURRET": {"rating": 0.0, "top": 0, "max": 100, "durability": 0, "crits": [], "crew": 1, "weapons": [],
                       "flags": {}},
            "FRONT": {"rating": 0.0, "top": 0, "max": 100, "durability": 0, "crits": [], "crew": 1, "weapons": [],
                      "flags": {}},
            "LEFT": {"rating": 0.0, "top": 0, "max": 100, "durability": 0, "crits": [], "crew": 0, "weapons": [],
                     "flags": {}},
            "RIGHT": {"rating": 0.0, "top": 0, "max": 100, "durability": 0, "crits": [], "crew": 0, "weapons": [],
                      "flags": {}},
            "BACK": {"rating": 0.0, "top": 0, "max": 100, "durability": 0, "crits": [], "crew": 0, "weapons": [],
                     "flags": {}}}

        sorted_keys = sorted(self.tank_parts, key=lambda my_key: self.tank_parts[my_key].get("rating", 0))

        for part_key in sorted_keys:

            part_number = self.tank_parts[part_key]["part"]
            location = self.tank_parts[part_key]["location"]
            part = self.parts_dict[part_number]

            section = section_dict[location]

            tons += part.get('weight', 0)
            cost += part.get('cost', 0) * (part['x_size'] * part['y_size'])

            global_flags = part.get("global_flags")

            if global_flags and global_flags not in special_effects:
                special_effects.append(global_flags)

            local_flags = part.get("local_flags")

            if local_flags == "crew":
                section["crew"] += 1

            section['durability'] += part['durability']

            if part['type'] == "armor":
                if location == "TURRET":
                    armor_scale = turret['armor_scale']
                else:
                    armor_scale = chassis['armor_scale']

                value = part.get('rating', 0) * armor_scale
                max_value = part.get('range', 100)

                local_flags = part.get("local_flags")
                if local_flags:
                    section['flags'][local_flags] = True

                if section['max'] > max_value:
                    section['max'] = max_value

                section['rating'] += value

            if part['type'] == "engine":

                if engine_rating == 0:
                    engine_rating += part['rating']
                else:
                    engine_rating += part['rating'] * 0.5

            if part['type'] == "suspension":
                if not suspension_type:
                    suspension_type = part['global_flags']

                if suspension_type == part['global_flags']:
                    suspension += part['rating']

            if part['type'] == "weapon":

                section['weapons'].append(part_number)

        for armor_key in section_dict:
            section = section_dict[armor_key]

            if section['flags'].get("compact"):
                section['rating'] = round(section['rating'] * 1.5)
            else:
                section['rating'] = round(section['rating'])

            if section['flags'].get("top_armor"):
                section['top'] = max(1, round(section['rating'] * 0.4))
            else:
                if section['rating'] > 0:
                    section['top'] = max(1, round(section['rating'] * 0.2))

            if section['rating'] > section['max']:
                section['rating'] = section['max']
            if section['top'] > section['max'] * 0.4:
                section['top'] = round(section['max'] * 0.4)

        self.tank_stats['sections'] = section_dict
        self.tank_stats['special'] = special_effects
        self.tank_stats["cost"] = cost
        self.tank_stats["suspension"] = suspension
        self.tank_stats["suspension_type"] = suspension_type
        self.tank_stats["engine_rating"] = engine_rating
        self.tank_stats["fuel_type"] = "gasoline"
        self.tank_stats["tons"] = max(1, tons)
        self.tank_stats["stability"] = stability

        self.get_global_effects()

        power_to_weight = round(self.tank_stats["engine_rating"] * 50 / self.tank_stats["tons"], 1)

        if not self.tank_stats["suspension_type"]:
            suspension_mods = self.suspension_dict["unsprung"]
        else:
            suspension_mods = self.suspension_dict[suspension_type]

        if self.tank_stats["suspension"] < self.tank_stats["tons"]:
            pass  # do something with overweight here

        on_road = power_to_weight * suspension_mods['on_road']
        off_road = power_to_weight * suspension_mods['off_road']

        self.tank_stats['on_road'] = int(on_road)
        self.tank_stats['off_road'] = int(off_road)

        stat_categories = ["tons", "cost", "suspension", "engine_rating", "on_road", "off_road", "stability"]

        stat_string = ""

        for category in stat_categories:
            entry = self.tank_stats[category]

            stat_string = "{}{}:{}\n".format(stat_string, category, round(entry, 1))

        ### armor display

        if self.turret_size:
            locations = ["FRONT", "LEFT", "RIGHT", "BACK", "TURRET"]
        else:
            locations = ["FRONT", "LEFT", "RIGHT", "BACK"]

        armor_string = "ARMOR:\n"
        hit_points_string = "DURABILITY:\n"
        crew_string = "CREW:\n"

        for location in locations:
            armor_amout = round(self.tank_stats['sections'][location]["rating"])
            armor_top = round(self.tank_stats['sections'][location]["top"])
            damage = self.tank_stats['sections'][location]['durability']
            crew = self.tank_stats['sections'][location]['crew']

            armor_string = "{}{}:{}-{}\n".format(armor_string, location[:1], armor_amout, armor_top)
            hit_points_string = "{}{}:{}\n".format(hit_points_string, location[:1], damage)
            crew_string = "{}{}:{}\n".format(crew_string, location[:1], crew)

        self.tank_stats_text['Text'] = "{}\n\n{}\n\n{}\n\n{}".format(stat_string, armor_string, hit_points_string,
                                                                     crew_string)

    def get_global_effects(self):

        special_effects = self.tank_stats['special']

        ### do something here with maintenace

        if "cooling" in special_effects:
            self.tank_stats["cost"] -= 12

        fuels = ["diesel", "high_octane"]

        for fuel in fuels:
            if fuel in special_effects:
                self.tank_stats["fuel_type"] = fuel

    def save_name(self):

        events = bge.logic.keyboard.events

        for event in events:
            if events[event] == 1:

                if event == 133:
                    self.save_name_text_content = self.save_name_text_content[:-1]
                else:
                    shift = self.check_shift_held()
                    character = bge.events.EventToCharacter(event, shift)

                    if len(self.save_name_text_content) < 10:
                        self.save_name_text_content += character

        self.save_name_text['Text'] = self.save_name_text_content

    def update(self):
        self.save_name()
        self.set_cursor()
        self.mouse_controls()
        self.press_buttons()
        self.place_items()


##############################
### external setup

def main_loop(cont):
    own = cont.owner

    if "loop" not in own:
        own['loop'] = MainLoop(own)
    else:
        own['loop'].update()


###################################

import bge

parts_dict = {"1": ["car engine", "engine", 0.5, 1, 1, 1, None, None, 1, None, "nothing", 1, "nothing",
                    "The smallest engine available.", 2, -1, None, "e", None, None],
              "2": ["small truck engine", "engine", 1, 2, 1, 2, None, None, 1, None, "nothing", 2, "nothing",
                    "A small truck engine.", 2, -1, None, "truck engine", None, None],
              "3": ["large truck engine", "engine", 1.5, 3, 1, 4, None, None, 1, None, "nothing", 2, "nothing",
                    "A heavy truck engine.", 2, -1, None, "truck engine", None, None],
              "4": ["tank engine", "engine", 2, 4, 1, 6, None, None, 1, None, "nothing", 3, "nothing",
                    "An engine specifically designed for tanks.", 2, -1, None, "tank engine", None, None],
              "5": ["aircraft engine", "engine", 3, 3, 2, 12, None, None, 1, None, "nothing", 4, "nothing",
                    "Very high performance, but high maintenance.", 1, -1, None, "aircraft engine", None, None],
              "6": ["naval engine", "engine", 4, 4, 2, 18, None, None, 1, None, "nothing", 3, "nothing",
                    "A very large engine for the biggest tanks.", 3, -1, None, "naval engine", None, None],
              "7": ["radial engine", "engine", 2, 4, 1, 8, None, None, 1, None, "nothing", 4, "nothing",
                    "A well balanced, compact engine.", 1, -1, None, "large radial engine", None, None],
              "8": ["diesel radial engine", "engine", 2, 4, 1, 7, None, None, 1, None, "nothing", 3, "diesel",
                    "A well balanced, compact engine.", 2, -1, None, "large radial engine", None, None],
              "9": ["diesel truck engine", "engine", 1, 2, 1, 3, None, None, 1, None, "nothing", 2, "diesel",
                    "A heavy diesel truck engine.", 3, -1, None, "truck (d)", None, None],
              "10": ["diesel tank engine", "engine", 2, 4, 1, 5, None, None, 1, None, "nothing", 3, "diesel",
                     "A reliable diesel engine specifically designed for tanks.", 3, -1, None, "tank (d)", None, None],
              "11": ["large diesel engine", "engine", 3, 3, 2, 10, None, None, 1, None, "nothing", 4, "diesel",
                     "A big high performance diesel engine.", 3, -1, None, "tank (d)+", None, None],
              "12": ["huge diesel engine", "engine", 4, 4, 2, 14, None, None, 1, None, "nothing", 3, "diesel",
                     "A very large diesel engine. Low maintenance.", 4, -1, None, "tank (d)++", None, None],
              "13": ["turboshaft engine", "engine", 2.5, 5, 1, 20, None, None, 1, None, "nothing", 12, "nothing",
                     "An experimental jet turbine engine.", 1, -1, None, "turboshaft", None, None],
              "14": ["extra fuel tank", "mechanical", 1, 2, 1, None, None, None, 1, None, "fuel", 2, "nothing",
                     "An extra fuel tank for greater range.", 1, -1, None, "fuel", None, None],
              "15": ["high octane fuel tank", "mechanical", 1, 2, 1, None, None, None, 1, None, "nothing", 3,
                     "high_octane", "A high octane fuel tank for high performance.", 1, -1, None, "fuel+", None, None],
              "16": ["improved air filters", "mechanical", 1, 2, 1, None, None, None, 1, None, "nothing", 1, "filters",
                     "A simple system provides additional cooling for the engine.", 2, -1, None, "f", None, None],
              "17": ["improved engine cooling", "mechanical", 1, 2, 1, None, None, None, 1, None, "nothing", 3,
                     "cooling", "An advanced system provides additional cooling for the engine.", 1, -1, None, "c",
                     None, None],
              "18": ["heavy duty transmission", "mechanical", 0.5, 1, 1, None, None, None, 1, None, "nothing", 2,
                     "transmission_1", "Improves reliability over the basic integrated gearbox.", 3, -1, None, "t",
                     None, None],
              "19": ["electrical transmission", "mechanical", 1, 2, 1, None, None, None, 1, None, "nothing", 3,
                     "transmission_2", "Improves transmission performance in large vehicles.", 2, -1, None,
                     "hydraulic drive", None, None],
              "20": ["wheeled", "suspension", 0.5, 1, 1, 2, None, 1, 1, None, "nothing", 1, "wheeled",
                     "Simple sprung wheel suspension. Good for trucks.", 1, -1, None, "w", None, None],
              "21": ["heavy-duty wheeled", "suspension", 0.5, 1, 1, 3, None, 1, 1, None, "nothing", 1, "wheeled",
                     "Heavier, more reliable wheels.", 2, -1, None, "w", None, None],
              "22": ["halftrack", "suspension", 0.5, 1, 1, 3, None, 2, 1, None, "nothing", 2, "halftrack",
                     "A mix of sprung and wheeled suspension.", 2, -1, None, "ht", None, None],
              "23": ["leaf spring", "suspension", 1, 2, 1, 7, None, 2, 1, None, "nothing", 2, "leaf_spring",
                     "Ordinary tank suspension", 2, -1, None, "leaf", None, None],
              "24": ["coil spring", "suspension", 0.5, 1, 1, 4, None, 1, 1, None, "nothing", 3, "coil_spring",
                     "Compact but weak suspension, easy to repair.", 1, -1, None, "coil", None, None],
              "25": ["bellcrank", "suspension", 1, 2, 1, 8, None, 1, 1, None, "nothing", 3, "bell_crank",
                     "Good all terrain performance, Quite unstable.", 2, -1, None, "bell crank", None, None],
              "26": ["torsion bar", "suspension", 1.5, 3, 1, 10, None, 3, 1, None, "nothing", 4, "torsion_bar",
                     "A well balanced, stable and robust system.", 3, -1, None, "torsion", None, None],
              "27": ["hydraulic", "suspension", 0.5, 1, 1, 6, None, 4, 1, None, "nothing", 5, "hydraulic_spring",
                     "Excellent performance, very stable, high maintenance.", 1, -1, None, "hydraulic springs", None,
                     None],
              "28": ["machine gun", "weapon", 0.5, 1, 1, 1, 2, 2, 1, 1, "small_arms", 3, "nothing",
                     "Good for anti-infantry duty.", 2, 0, 4, "m g", None, None],
              "29": ["improved machinegun", "weapon", 0.5, 1, 1, 1, 2, 3, 1, 1, "small_arms", 5, "nothing",
                     "An excellent upgrade for anti-infantry duty.", 2, 0, 2, "m g+", None, None],
              "30": ["heavy machinegun", "weapon", 1, 2, 1, 2, 2, 1, 1, 1, "small_arms", 2, "nothing",
                     "Good vs infantry and light vehicles.", 2, 0, 4, "hmg", None, None],
              "31": ["anti tank rifle", "weapon", 0.5, 1, 1, 2, 2, 3, 1, 2, "small_arms", 1, "nothing",
                     "A light, man portable weapon fitted to a vehicle.", 1, 0, 4, "at rifle", None, None],
              "32": ["autocannon", "weapon", 1, 2, 1, 2, 2, 2, 1, 2, "rapid", 4, "nothing",
                     "Good vs infantry and light vehicles.", 2, 0, 4, "auto cannon", None, None],
              "33": ["heavy autocannon", "weapon", 3, 3, 2, 4, 2, 1, 1, 3, "rapid", 4, "nothing",
                     "Spits out a large volume of fire. Needs lots of ammo.", 2, 0, 4, "heavy autocannon", None, None],
              "34": ["support gun", "weapon", 2, 4, 1, 8, 3, 1, 1, 4, "low_velocity", 2, "nothing",
                     "Not accurate, low penetration at range. Good vs buildings.", 3, 0, 4, "support gun", None, None],
              "35": ["heavy support gun", "weapon", 3, 6, 1, 15, 3, 1, 1, 5, "low_velocity", 2, "nothing",
                     "Not accurate, low penetration at range. Good vs buildings.", 3, 0, 12, "heavy support gun", None,
                     None],
              "36": ["howitzer", "weapon", 6, 6, 2, 11, 4, 2, 1, 6, "open_sights", 2, "nothing",
                     "Large, lack of gun sights make it ill suited to close combat.", 3, 0, 8, "howitzer", None, None],
              "37": ["heavy howitzer", "weapon", 9, 6, 3, 15, 4, 2, 1, 7, "open_sights", 2, "nothing",
                     "Huge, lack of gun sights make it ill suited to close combat.", 3, 0, 12, "heavy howitzer", None,
                     None],
              "38": ["light gun", "weapon", 1, 2, 1, 4, 2, 3, 1, 2, "nothing", 1, "nothing", "A good early tank gun.",
                     2, 0, 4, "light gun", None, None],
              "39": ["medium gun", "weapon", 2, 2, 2, 6, 2, 3, 1, 3, "nothing", 1, "nothing",
                     "A slight upgrade of the basic tank gun.", 3, 0, 8, "medium gun", None, None],
              "40": ["heavy gun", "weapon", 3, 3, 2, 8, 3, 3, 1, 3, "nothing", 1, "nothing",
                     "A conversion of a light field gun, readily available.", 3, 0, 8, "heavy gun", None, None],
              "41": ["super heavy gun", "weapon", 9, 6, 3, 12, 4, 3, 1, 8, "nothing", 1, "nothing",
                     "High damage, but not high velocity. Slow reload time.", 3, 0, 16, "super heavy gun", None, None],
              "42": ["improved light gun", "weapon", 2, 2, 2, 6, 3, 4, 1, 3, "high_velocity", 2, "nothing",
                     "Gives anti tank capability to light vehicles.", 3, 0, 4, "light gun+", None, None],
              "43": ["improved medium gun", "weapon", 5, 5, 2, 8, 4, 4, 1, 6, "high_velocity", 2, "nothing",
                     "A really good anti tank gun.", 3, 0, 8, "medium gun+", None, None],
              "44": ["improved heavy gun", "weapon", 9, 6, 3, 9, 4, 5, 1, 7, "high_velocity", 2, "nothing",
                     "Best penetration, very accurate, good damage.", 3, 0, 12, "heavy gun+", None, None],
              "45": ["flamethrower", "weapon", 3, 3, 2, 2, 1, 4, 1, 2, "flamer", 4, "nothing",
                     "Very high damage potential but very short range.", 1, 0, 2, "flamer", None, None],
              "46": ["mortar", "weapon", 2, 2, 2, 8, 3, 1, 1, 4, "mortar", 1, "nothing",
                     "A simple artillery weapon. Low rate of fire but good damage.", 1, 0, 12, "mortar", None, None],
              "47": ["heavy mortar", "weapon", 4, 4, 2, 16, 3, 1, 1, 5, "mortar", 1, "nothing",
                     "A very slow rate of fire, but great damage to weight potential.", 2, 0, 16, "heavy mortar", None,
                     None],
              "48": ["small rockets", "weapon", 0.5, 1, 1, 8, 4, 2, 1, 9, "rockets", 4, "nothing",
                     "Long range rockets with a small warhead.", 1, 0, 1, "rkts", None, None],
              "49": ["large rockets", "weapon", 1, 2, 1, 15, 3, 1, 1, 9, "rockets", 4, "nothing",
                     "Short range rockets with a large warhead.", 1, 0, 1, "large rockets", None, None],
              "50": ["applique patch", "armor", 0.5, 1, 1, 1, None, None, 1, None, "crit_reduction", 1, "nothing",
                     "Applied to critical areas. Reduced chance of critical hit.", 2, 0, None, "p", None, None],
              "51": ["spaced armor skirts", "armor", 1, 2, 1, 1, None, None, 1, None, "anti_HEAT", 1, "nothing",
                     "Protects against HEAT attacks.", 1, 0, None, "ss", None, None],
              "51": ["extra top armor", "armor", 1, 2, 1, 1, None, None, 1, None, "top_armor", 1, "nothing",
                     "Top armor in this location increased.", 1, 0, None, "top", None, None],
              "52": ["sloped arrangement", "armor", 1, 2, 1, 1, None, None, 1, None, "sloped", 1, "nothing",
                     "Sloped armor in this location, chance of deflecting shots.", 1, 0, None, "sloped", None, None],
              "53": ["compact arrangement", "armor", 1, 2, 1, 1, None, None, 1, None, "compact", 1, "nothing",
                     "Better lay out of armor increases armor effectiveness.", 1, 0, None, "compact", None, None],
              "54": ["riveted plate", "armor", 0.5, 1, 1, 1, 8, None, 1, None, "spalling", 1, "nothing",
                     "Not robust, however easy to make with simple techniques.", 2, 0, None, "r", None, None],
              "55": ["small cast section", "armor", 1, 2, 1, 2, 8, None, 1, None, "spalling", 2, "nothing",
                     "Easy to make but can have flaws.", 2, 0, None, "cast", None, None],
              "56": ["face hardened plate", "armor", 0.5, 1, 1, 1, 4, None, 1, None, "nothing", 2, "nothing",
                     "Welded, good protection in thin sheets, light.", 1, 0, None, "h", None, None],
              "57": ["medium rolled plate", "armor", 1, 2, 1, 2, 10, None, 1, None, "nothing", 2, "nothing",
                     "Sheets often layered and welded so not as strong.", 2, 0, None, "rolled plate", None, None],
              "58": ["large rolled plate", "armor", 2, 4, 1, 4, 16, None, 1, None, "nothing", 2, "nothing",
                     "Welded, standard armor. Strong and shock resistant.", 2, 0, None, "rolled plate", None, None],
              "59": ["large cast section", "armor", 3, 3, 2, 6, 24, None, 1, None, "nothing", 1, "nothing",
                     "Requires special techniques to make large sections.", 2, 0, None, "large cast", None, None],
              "60": ["composite armor", "armor", 1, 2, 1, 2, 12, None, 1, None, "composite", 3, "nothing",
                     "Experimental metal and glass composite. Resists HEAT.", 1, 0, None, "composite", None, None],
              "61": ["extra ammo", "utility", 1, 2, 1, None, None, None, 1, None, "ammo", 4, "standard_shells",
                     "Extra supplies of normal bullet, shell and shot types", 1, 0, None, "extra ammo", None, None],
              "62": ["special ammo", "utility", 1, 2, 1, None, None, None, 1, None, "ammo", 4, "special_shells",
                     "Special utility shells such as smoke.", 1, 0, None, "special ammo", None, None],
              "63": ["improved ammo", "utility", 1, 2, 1, None, None, None, 1, None, "ammo", 8, "improved_shells",
                     "Improved ammo types where available.", 1, 0, None, "imp ammo", None, None],
              "64": ["advanced ammo", "utility", 1, 2, 1, None, None, None, 1, None, "ammo", 12, "advanced_shells",
                     "advanced shaped charge rounds.", 1, 0, None, "adv ammo", None, None],
              "65": ["improved gun sights", "utility", 0.5, 1, 1, None, None, None, 1, "None", "gun_sights", 4,
                     "nothing", "Weapons in this section have improved sights.", 1, 0, None, "(+)", None, None],
              "66": ["advanced sights", "utility", 1, 2, 1, None, None, None, 1, "None", "gun_sights", 12,
                     "night_vision", "Night vision and imroved sights.", 1, 0, None, "sight +", None, None],
              "67": ["binocular periscope", "utility", 0.5, 1, 1, None, None, None, 1, "None", "gun_sights", 1,
                     "vision_2", "Better viewing range. Can spot hidden enemies easier.", 1, 0, None, "b", None, None],
              "68": ["commanders cupola", "utility", 0.5, 1, 1, None, None, None, 1, "None", "gun_sights", 1,
                     "vision_1", "Better viewing range. Can spot hidden enemies easier.", 1, 0, None, "cc", None, None],
              "69": ["gyroscopic stabilizer", "utility", 1, 2, 1, None, None, None, 1, "None", "stabilized", 3,
                     "nothing", "All guns in this section stabilized for move and fire.", 2, 0, None, "gyro", None,
                     None],
              "70": ["radio", "utility", 0.5, 1, 1, None, None, None, 1, "None", "nothing", 4, "radio",
                     "Gives more flexibility and awareness in combat.", 1, 0, None, "[r]", None, None],
              "71": ["high power antenna", "utility", 1.5, 3, 1, None, None, None, 1, "None", "nothing", 4, "antenna",
                     "Gives better tactical choices. Requires a radio.", 1, 0, None, "antenna", None, None],
              "72": ["improved muzzle breaks", "utility", 0.5, 1, 1, None, None, None, 1, "None", "muzzle_break", 2,
                     "nothing", "Weapons in this section have reduced recoil.", 3, 0, None, "mb", None, None],
              "73": ["engineering tools", "utility", 1.5, 3, 1, None, None, None, 1, "None", "supplies", 6,
                     "engineering", "Tools and equipment used by engineers.", 1, 0, None, "engineering tools", None,
                     None],
              "74": ["storage space", "utility", 0.5, 1, 1, None, None, None, 1, "None", "supplies", 4, "supplies",
                     "Can carry half a ton of supplies or two infantry men.", 1, -1, None, "[s]", None, None],
              "75": ["amphibious adaptation", "utility", 1, 2, 1, 3, None, None, 1, "None", "engine", 2, "amphibious",
                     "Avoid bogging down in water.", 3, -1, None, "amphibious", None, None],
              "76": ["extra crew", "utility", 1, 2, 1, None, None, None, 1, "None", "crew", 1, "nothing",
                     "Extra crew for manning weapons and other tasks.", 1, 0, None, "extra crew", None, None],
              "77": ["fire extinguisher", "utility", 0.5, 1, 1, None, None, None, 1, "None", "nothing", 2, "extinguish",
                     "Gives a chance to extinguish on-board fires.", 1, 0, None, "fx", None, None],
              "78": ["machine tools", "utility", 1, 2, 1, None, None, None, 1, "None", "nothing", 3, "repair",
                     "Can try to make minor repairs in the field.", 2, 0, None, "tools", None, None],
              "79": ["extra wide tracks", "mechanical", 1, 2, 1, None, None, None, 1, "None", "nothing", 1,
                     "wide_tracks", "Better traction on soft terrain.", 1, -1, None, "[t]", None, None],
              "80": ["semi automatic loader", "mechanical", 1, 2, 1, None, None, None, 1, "None", "auto_loader", 3,
                     "nothing", "Reloads large guns more quickly than normal.", 1, 0, None, "auto loader", None, None],
              "81": ["spare parts", "mechanical", 0.5, 1, 1, None, None, None, 1, "None", "nothing", 2, "spares",
                     "Improves reliability in the field.", 3, 0, None, "sp", None, None],
              "82": ["dual turrets", "mechanical", 1.5, 3, 1, None, None, None, 1, "None", "nothing", 3, "dual_turret",
                     "A single turret is replaced by two smaller ones.", 2, 1, None, "dual turrets", None, None],
              "83": ["mini turret", "mechanical", 1, 2, 1, None, None, None, 1, "None", "mini_turret", 2, "nothing",
                     "Any small arms on this location will be mounted in a mini turret.", 3, 0, None, "mini turret",
                     None, None],
              "84": ["super charger", "mechanical", 1, 2, 1, None, None, None, 1, "None", "engine", 12, "super_charger",
                     "Allows more speed at the cost of increased maintenance.", 1, -1, None, "super charger", None,
                     None],
              "85": ["improved turret control", "mechanical", 1, 2, 1, None, None, None, 1, "None", "nothing", 4,
                     "turret_speed", "Larger turrets can turn faster.", 2, 1, None, "turret control", None, None]}

labels = ["name",
          "type",
          "weight",
          "x_size",
          "y_size",
          "rating",
          "range",
          "stability",
          "tech_level",
          "weapon_size",
          "local_flags",
          "cost",
          "global_flags",
          "description",
          "durability",
          "turret_only",
          "rate_of_fire",
          "short_name",
          "requirement_1",
          "requirement_2"]


def get_parts():
    new_part_dictionary = {}

    for part_key in parts_dict:
        part = parts_dict[part_key]

        new_part_dict = {}

        for e in range(len(part)):
            entry = part[e]
            if entry != None:
                if entry != "nothing":
                    label = labels[e]
                    new_part_dict[label] = entry

        new_part_dictionary[part_key] = new_part_dict

    return new_part_dictionary


def get_chassis_dict():
    chassis_dict = {"1": {"x": 2, "y": 6, "name": "mini chassis", "front": 3, "back": 1, "armor_scale": 1.1},
                    "2": {"x": 4, "y": 8, "name": "small chassis", "front": 4, "back": 2, "armor_scale": 1.05},
                    "3": {"x": 6, "y": 10, "name": "medium chassis", "front": 6, "back": 3, "armor_scale": 1.0},
                    "4": {"x": 8, "y": 12, "name": "large chassis", "front": 7, "back": 4, "armor_scale": 0.95},
                    "5": {"x": 12, "y": 15, "name": "huge chassis", "front": 8, "back": 4, "armor_scale": 0.9}}

    return chassis_dict


def get_turret_dict():
    turret_dict = {"0": {"x": 0, "y": 0, "name": "no turret", "block_x": 0, "block_y": 0, "armor_scale": 0},
                   "1": {"x": 2, "y": 1, "name": "mini turret", "block_x": 1, "block_y": 1, "armor_scale": 1.25},
                   "2": {"x": 2, "y": 2, "name": "small turret", "block_x": 2, "block_y": 1, "armor_scale": 1.2},
                   "3": {"x": 4, "y": 3, "name": "medium turret", "block_x": 2, "block_y": 2, "armor_scale": 1.15},
                   "4": {"x": 6, "y": 4, "name": "large turret", "block_x": 4, "block_y": 2, "armor_scale": 1.1},
                   "5": {"x": 8, "y": 5, "name": "huge turret", "block_x": 6, "block_y": 3, "armor_scale": 1.0},
                   "6": {"x": 10, "y": 7, "name": "giant turret", "block_x": 8, "block_y": 4, "armor_scale": 0.95}}

    return turret_dict


def get_suspension_dict():
    suspension_dict = {"wheeled": {"on_road": 4, "off_road": 1},
                       "halftrack": {"on_road": 3.2, "off_road": 1.8},
                       "leaf_spring": {"on_road": 2.8, "off_road": 1.9},
                       "coil_spring": {"on_road": 2.5, "off_road": 2},
                       "bell_crank": {"on_road": 2.7, "off_road": 2},
                       "torsion_bar": {"on_road": 3, "off_road": 2.1},
                       "hydraulic_spring": {"on_road": 3, "off_road": 2.1},
                       "unsprung": {"on_road": 0.8, "off_road": 0.56}}

    return suspension_dict


