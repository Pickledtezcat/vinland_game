import bge
import bgeutils
from mathutils import Vector


def split_string_in_lines(contents, line_length):
    words = contents.split()

    new_line = []
    lines = []
    letters = 0

    for word in words:
        letters += len(word)

        if letters < line_length:
            new_line.append(word)
        else:
            lines.append(" ".join(new_line))
            new_line = [word]
            letters = len(word)

    if new_line:
        lines.append(" ".join(new_line))

    new_contents = "\n".join(lines)

    return new_contents


class Tile(object):
    def __init__(self, x, y, location, weapon_location):
        self.x = x
        self.y = y

        self.part = None
        self.location = location
        self.weapon_location = weapon_location
        self.parent_tile = None
        self.rotated = False


class VehicleRepresentation(object):
    def __init__(self, vehicle_stats):
        pass


class VehicleDisplay(object):
    def __init__(self, manager, parent, turret):
        self.manager = manager
        self.parent = parent

        self.vehicle_stats = self.manager.vehicle_stats

        display_window = "vehicle_display_box"

        if turret:
            display_window = "vehicle_display_box_t"

        self.display_window = self.parent.scene.addObject(display_window, parent, 0)
        self.vehicle_representation = VehicleRepresentation(self.vehicle_stats)

        sections = ["FRONT", "LEFT", "RIGHT", "BACK", "TURRET"]

        for section in sections:
            display_text = bgeutils.get_ob(section, self.display_window.children)
            if display_text:
                current_section = self.vehicle_stats['sections'][section]

                components = [str(int(current_section["durability"])).zfill(2), str(int(current_section["rating"])).zfill(2), str(int(current_section["top"])).zfill(2)]

                text_string = "{}:{}/{}/{}".format(section, *components)
                display_text['Text'] = text_string

    def update(self):
        pass

    def end_button(self):
        self.display_window.endObject()


class Button(object):
    def __init__(self, manager, button_size, name, label_text, location, part_key=None, color=None, mouse_over=None,
                 text_box=False, scale=1.0, text_entry=False):
        self.manager = manager
        self.name = name
        self.part_key = part_key

        self.button_size = button_size

        self.on_mesh = "{}_on".format(self.button_size)
        self.off_mesh = "{}_off".format(self.button_size)

        self.object_box = self.manager.scene.addObject(self.off_mesh, self.manager.own, 0)

        if text_box:
            self.off_mesh = self.on_mesh
            self.object_box.replaceMesh(self.off_mesh)

        self.object_box['button_click'] = True
        self.object_box['button_owner'] = self
        self.object_box['mouse_over'] = bgeutils.add_spaces(mouse_over)

        if color:
            self.color = color
        else:
            self.color = [1.0, 1.0, 1.0, 1.0]

        self.object_box.color = self.color
        self.object_box.worldPosition = location

        self.text_object = bgeutils.get_ob("button_text", self.object_box.children)

        self.text_entry = text_entry

        if self.text_entry:
            self.focus = False
            self.text_contents = ""
            self.text_object['Text'] = ""
        else:
            self.text_object['Text'] = bgeutils.add_spaces(label_text)

        large_boxes = ["image_box", "text_box", "large_text_box"]
        if button_size not in large_boxes:
            length = len(label_text.split("\n"))
            if length == 1:
                self.text_object.localPosition.y -= 0.18

            elif length % 2 == 0:
                self.text_object.localPosition.y -= 0.09

        self.text_object.color = [1.0, 1.0, 1.0, 1.0]
        self.text_object.resolution = 8

        self.object_box.localScale *= scale

        self.clicked = False
        self.redrawn = False
        self.click_timer = 0

    def end_button(self):
        self.object_box.endObject()

    def update(self):

        if self.text_entry:
            if self.clicked:
                self.clicked = False
                self.focus = not self.focus
                if self.focus:
                    if not self.redrawn:
                        self.object_box.replaceMesh(self.on_mesh)
                        self.text_object.color = Vector(self.color) * 0.5
                        self.redrawn = True
                        self.text_contents = ""

                else:
                    self.object_box.replaceMesh(self.off_mesh)
                    self.text_object.color = [1.0, 1.0, 1.0, 1.0]
                    self.redrawn = False

            elif self.focus:
                keys_pressed = bge.logic.keyboard.events
                for pressed_key in keys_pressed:

                    if keys_pressed[pressed_key] == 1:
                        if int(pressed_key) == 133:
                            self.text_contents = self.text_contents[:len(self.text_contents) - 1]
                        elif int(pressed_key) == 134:
                            self.text_contents = ""
                        else:
                            self.text_contents += bge.events.EventToCharacter(pressed_key, False)

                self.text_contents = self.text_contents[:15]
                self.text_object['Text'] = self.text_contents

        elif self.clicked:
            if self.click_timer > 12:
                self.object_box.replaceMesh(self.off_mesh)
                self.text_object.color = [1.0, 1.0, 1.0, 1.0]
                self.clicked = False
                self.redrawn = False
                self.click_timer = 0
            else:
                if not self.redrawn:
                    self.object_box.replaceMesh(self.on_mesh)
                    self.text_object.color = Vector(self.color) * 0.5
                    self.redrawn = True
                self.click_timer += 1


