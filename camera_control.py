import bge
import mathutils

import bgeutils

class CameraControl(object):

    def __init__(self, manager):
        self.manager = manager

        self.main_camera = self.manager.scene.active_camera
        self.camera_hook = bgeutils.get_ob("camera_hook", self.manager.scene.objects)
        self.shadow_light = bgeutils.get_ob("shadow_light", self.manager.scene.objects)
        self.shadow_light_in = 60
        self.shadow_light_out = 110
        self.zoom_in_hook = bgeutils.get_ob("zoom_in", self.manager.scene.objects)
        self.zoom_out_hook = bgeutils.get_ob("zoom_out", self.manager.scene.objects)
        self.on_edge = False
        self.pan_speed = 0.0
        self.pan_vector = mathutils.Vector()

        self.zoomer = None
        self.zoom = True

    def update(self):
        self.control_zoom()
        self.control_movement()

    def control_movement(self):
        x, y = self.manager.input.virtual_mouse

        self.on_edge = x > 0.99 or x < 0.01 or y > 0.99 or y < 0.01
        if self.on_edge:
            self.pan_speed = max(0.0, (min(0.13, self.pan_speed + 0.001)))
            self.pan_vector = mathutils.Vector([x - 0.5, 0.5 - y, 0.0])

        else:
            self.pan_speed = max(0.0, (min(0.1, self.pan_speed - 0.003)))

        if self.pan_speed > 0.01:

            self.pan_vector.length = self.pan_speed

            if self.zoom:
                modifier = 16.0
            else:
                modifier = 32.0

            self.pan_vector.length *= modifier

            cam_vector = self.pan_vector.copy()
            cam_vector.rotate(self.camera_hook.worldOrientation)
            self.camera_hook.worldPosition += cam_vector

    def control_zoom(self):

        if not self.zoomer:
            if not self.zoom:
                if "plus" in self.manager.input.keys or "wheel_up" in self.manager.input.buttons:
                    self.zoomer = ZoomerIn(self)
                    self.zoom = True

            if self.zoom:
                if "minus" in self.manager.input.keys or "wheel_down" in self.manager.input.buttons:
                    self.zoomer = ZoomerOut(self)
                    self.zoom = False

        else:
            if self.zoomer.done:
                self.zoomer = None
            else:
                self.zoomer.update()


class ZoomerIn(object):
    def __init__(self,controller):

        self.controller = controller
        self.start = self.controller.zoom_out_hook.localTransform
        self.end = self.controller.zoom_in_hook.localTransform
        self.speed = 0.03
        self.timer = 0.0
        self.done = False

    def update(self):

        if self.timer >= 1.0:
            self.done = True
        else:
            self.timer = min(1.0, self.timer + self.speed)
            amount = bgeutils.smoothstep(self.timer)
            self.controller.main_camera.localTransform = self.start.lerp(self.end, amount)
            light_in = self.controller.shadow_light_in
            light_out = self.controller.shadow_light_out
            self.controller.shadow_light.spotsize = bgeutils.interpolate_float(light_out, light_in, amount)


class ZoomerOut(object):
    def __init__(self,controller):

        self.controller = controller
        self.start = self.controller.zoom_in_hook.localTransform
        self.end = self.controller.zoom_out_hook.localTransform
        self.speed = 0.03
        self.timer = 0.0
        self.done = False

    def update(self):

        if self.timer >= 1.0:
            self.done = True
        else:
            self.timer = min(1.0, self.timer + self.speed)
            amount = bgeutils.smoothstep(self.timer)
            self.controller.main_camera.localTransform = self.start.lerp(self.end, amount)
            light_in = self.controller.shadow_light_in
            light_out = self.controller.shadow_light_out
            self.controller.shadow_light.spotsize = bgeutils.interpolate_float(light_in, light_out, amount)