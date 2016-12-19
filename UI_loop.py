import bge
import mathutils
import random
import math
import logging
import time
import game_states

import bgeutils


class UILoop(object):
    def __init__(self, cont, main_loop):

        self.cont = cont
        self.own = cont.owner
        self.scene = cont.owner.scene
        self.main_loop = main_loop
        self.main_camera = self.scene.active_camera
        self.debug_text = bgeutils.get_ob("debug_text", self.scene.objects)

        self.cursor = self.scene.addObject("cursor_ob", self.own, 0)
        self.cursor_mesh = self.cursor.children[0]
        self.cursor_default = mathutils.Vector([-1.0, 1.0, 0.0])
        self.selection_box = None

        self.state_name = None
        self.state = game_states.UISetUp(self)

    def update(self):
        self.profile("ui_state_machine")

    def ui_state_machine(self):
        self.state.update()

        next_state = self.state.transition()
        if next_state:
            self.state.end()
            self.state = next_state(self)
            self.state_name = next_state.__name__

    def set_cursor(self, mesh_name):
        self.cursor_mesh.replaceMesh(mesh_name)

    def draw_selection_box(self):
        if self.selection_box:
            self.selection_box.endObject()
            self.selection_box = None

        if self.main_loop.select_point:

            start = self.main_loop.select_point
            end = self.main_loop.input.virtual_mouse.copy()

            x_limit = sorted([start[0], end[0]])
            y_limit = sorted([start[1], end[1]])

            self.selection_box = self.scene.addObject("select_box", self.own, 0)

            start_vector = self.main_camera.getScreenVect(x_limit[0], y_limit[0])
            start_vector.length = 19.5

            end_vector = self.main_camera.getScreenVect(x_limit[1], y_limit[1])
            end_vector.length = 19.5

            x_length = start_vector[0] - end_vector[0]
            y_length = start_vector[1] - end_vector[1]

            self.selection_box.worldPosition = self.main_camera.worldPosition.copy() - start_vector
            self.selection_box.localScale.x = x_length
            self.selection_box.localScale.y = y_length

    def game_cursor_update(self):

        if self.main_loop.context == "PAN":
            self.set_cursor("pan_cursor")
        elif self.main_loop.context == "SELECT":
            self.set_cursor("select_cursor")
        elif self.main_loop.context == "TARGET":
            self.set_cursor("target_cursor")
        elif self.main_loop.context == "NO_TARGET":
            self.set_cursor("no_target_cursor")

        self.debug_text['Text'] = self.main_loop.debug_message

        mouse_x, mouse_y = self.main_loop.input.virtual_mouse
        cursor_vector = self.main_camera.getScreenVect(mouse_x, mouse_y)
        cursor_vector.length = 19.5
        cursor_location = self.main_camera.worldPosition.copy() - cursor_vector

        if self.main_loop.camera.on_edge:
            target = self.main_loop.camera.pan_vector.normalized().to_track_quat("Y", "Z").to_matrix().to_4x4()
            self.cursor.localTransform = self.cursor.localTransform.lerp(target, 0.1)

        else:
            target = self.cursor_default.normalized().to_track_quat("Y", "Z").to_matrix().to_4x4()
            self.cursor.localTransform = self.cursor.localTransform.lerp(target, 0.3)

        self.cursor.worldPosition = cursor_location

    def profile(self, method_name, one_time=False):

        loop_methods = {"draw_selection_box": self.draw_selection_box,
                        "game_cursor_update": self.game_cursor_update,
                        "ui_state_machine": self.ui_state_machine}

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
            self.main_loop.debug_timer[method_name] = "{:<30}:{:>12}ms {}".format(method_string, time_string, finished)

        else:
            print("not method called [{}] on UI loop".format(method_name))
