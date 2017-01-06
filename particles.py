import bge
import bgeutils

import mathutils
import random
import math


class Particle(object):
    def __init__(self, manager, owner):
        self.manager = manager
        self.manager.particles.append(self)
        self.owner = owner
        self.can_pause = True

        self.object_box = None
        self.ended = False
        self.life = 0
        self.maximum_life = 0
        self.frame = 0
        self.sub_frame = 0
        self.max_frame = 0
        self.max_sub_frame = 0
        self.mesh_name = None
        self.sound = None

        self.light = False
        self.light_energy = 1.0
        self.light_color = mathutils.Vector([1.0, 1.0, 1.0])
        self.light_distance = 25.0

    def end_object_box(self):
        if self.object_box:
            self.object_box.endObject()
            self.object_box = None

        if self.sound:
            self.sound.stop()

    def switch_frame(self):
        frame_name = "{}.{}".format(self.mesh_name, str(self.frame).zfill(3))
        self.object_box.replaceMesh(frame_name)

    def frame_update(self):

        if self.sub_frame < self.max_sub_frame:
            self.sub_frame += 1
        else:
            self.frame += 1
            self.sub_frame = 0
            self.switch_frame()

            if self.frame == self.max_frame:
                self.frame = 1

    def update(self):

        active = True

        if self.can_pause:
            if self.manager.paused:
                active = False

        if active:
            self.process()

    def process(self):

        if self.object_box and self.object_box.meshes:
            color = sum(list(self.object_box.color)[:3])
            alpha = self.object_box.color[3]

            if color < 0.01:
                self.ended = True

            if alpha < 0.1:
                self.ended = True

            if self.object_box.localScale.x < 0.01:
                self.ended = True

        if self.maximum_life:
            if self.life >= self.maximum_life:
                self.ended = True

        self.life += 1


class MovementPointIcon(Particle):
    def __init__(self, manager, owner, position):
        super().__init__(manager, owner)
        self.can_pause = False

        self.object_box = self.owner.scene.addObject("movement_point", self.owner, 0)
        self.set_position(position)
        self.object_box.color = [0.0, 1.0, 0.0, 1.0]

        self.light = True
        self.light_energy = 6.0
        self.light_color = mathutils.Vector([0.0, 1.0, 0.0])
        self.invalid_location = False

        self.released = False

    def set_position(self, position):

        self.invalid_location = False

        for axis in position:
            if axis < 0.0 or axis > self.manager.level_size * 8:
                self.invalid_location = True

        if self.invalid_location:
            position = position.to_3d()
            normal = mathutils.Vector([0.0, 0.0, 1.0])
        else:
            ground_hit_position = self.manager.tiles[bgeutils.get_key(position)]
            position = ground_hit_position.point
            normal = ground_hit_position.normal

        self.object_box.worldPosition = position
        self.object_box.worldPosition.z += 0.5
        self.object_box.alignAxisToVect(normal)

    def process(self):
        super().process()

        if self.released:
            self.object_box.localScale *= 0.9
            self.light_energy *= 0.9


class DebugMessage(Particle):
    def __init__(self, manager, owner, character, color):
        super().__init__(manager, owner)

        self.can_pause = False

        self.character = character
        self.object_box = self.owner.scene.addObject("message_text", self.owner, 0)
        self.text_object = self.object_box.children[0]
        self.text_object.color = color
        self.maximum_life = 0

        self.billboard_effect = True

    def process(self):
        super().process()

        if self.manager.debug:
            self.text_object.visible = True
            self.text_object['Text'] = self.character.debug_message
            owner_position = self.owner.worldPosition.copy()
            self.object_box.worldPosition = owner_position
            self.object_box.worldPosition.z += 5.0

        else:
            self.text_object.visible = False


class Dust(Particle):
    def __init__(self, manager, owner, size, off_road):
        super().__init__(manager, owner)

        dust_object, dust_color, dust_size = bge.logic.globalDict['dirt'][off_road]

        self.object_box = self.manager.scene.addObject(dust_object, self.manager.own, 0)
        self.object_box.worldPosition = self.owner.worldPosition.copy()
        self.mesh_name = dust_object

        self.object_box.color = dust_color
        self.object_box.localScale *= (size * dust_size)

        self.frame = random.randint(1, 4)
        self.sub_frame = 0
        self.max_sub_frame = 6
        self.max_frame = 4

        self.switch_frame()

        self.fade = 0.95
        self.grow = mathutils.Vector([bgeutils.rand_axis(0.1), bgeutils.rand_axis(0.05), 0.1])

    def process(self):
        super().process()

        self.grow.length *= 0.9
        self.object_box.localScale *= (1.0 + self.grow.length)

        self.object_box.color[3] *= self.fade
        self.object_box.worldPosition += self.grow


class Track(Particle):
    def __init__(self, manager, owner, ground_normal):
        super().__init__(manager, owner)

        self.object_box = self.manager.scene.addObject("track_trail", self.manager.own, 0)
        self.object_box.worldPosition = self.owner.worldPosition.copy()
        self.object_box.color = bge.logic.globalDict['tracks']
        self.ground_normal = ground_normal

        self.dropped = False
        self.finished = False

        self.track_timer = 0.0

    def align_tracks(self):

        target_vector = self.owner.worldPosition.copy() - self.object_box.worldPosition.copy()
        length = target_vector.length

        z = self.ground_normal.copy()

        if length > 0.0:
            y = target_vector
        else:
            y = self.owner.getAxisVect([0.0, 1.0, 0.0])
            length = 0.01

        self.object_box.alignAxisToVect(y, 1, 1.0)
        self.object_box.alignAxisToVect(z, 2, 1.0)

        self.object_box.localScale.y = length

    def process(self):
        super().process()

        if not self.finished:

            if self.track_timer <= 0.0:
                self.track_timer = 1.0
                self.align_tracks()

            else:
                self.track_timer -= 0.05

        else:
            self.object_box.color[3] *= 0.99

        if self.dropped and not self.finished:
            self.align_tracks()
            self.dropped = False
            self.finished = True




