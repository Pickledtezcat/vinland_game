import bgeutils
import bge
import mathutils
import math


class VisionPaint(object):
    def __init__(self, manager):
        self.manager = manager
        self.scene = self.manager.scene
        self.camera = self.scene.active_camera
        self.ground = [ob for ob in self.scene.objects if ob.get("vision_object")][0]
        self.canvas_size = 64
        self.brush_size = 32

        self.vision_brush = self.create_brush(6, [0, 0, 255], outer=15, smooth=True)

        self.player_pixel = self.create_brush(1, [0, 255, 0])
        self.enemy_pixel = self.create_brush(1, [255, 0, 0])
        self.spy_brushes = self.create_spy_brushes()

        self.brush_number = 4
        self.cave_list = None

        self.canvas = self.create_canvas()

        self.refresh_timer = 0
        self.max_refresh = 1

    def create_canvas(self):
        canvas_size = self.canvas_size

        tex = bge.texture.Texture(self.ground, 0, 0)
        tex.source = bge.texture.ImageBuff(color=0)

        tex.source.load(b'\x00\x00\x00' * (canvas_size * canvas_size), canvas_size, canvas_size)

        return tex

    def create_brush(self, radius, RGB, outer=0, smooth=False):

        brush_size = self.brush_size
        brush = bytearray(brush_size * brush_size * 4)
        center = mathutils.Vector([brush_size * 0.5, brush_size * 0.5])
        rgb = RGB
        half_rgb = [int(color * 0.5) for color in rgb]

        for x in range(brush_size):
            for y in range(brush_size):
                i = y * (brush_size * 4) + x * 4
                location = mathutils.Vector([x, y])
                target_vector = location - center
                length = target_vector.length

                if length == radius and smooth:
                    pixel = half_rgb
                elif length > radius:
                    if outer > 0 and length < outer:
                        pixel = half_rgb
                    else:
                        pixel = [0, 0, 0]
                else:
                    pixel = rgb

                brush[i] = pixel[0]
                brush[i + 1] = pixel[1]
                brush[i + 2] = pixel[2]
                brush[i + 3] = 255

        return brush

    def create_spy_brushes(self):

        directions_dict = {(-1, -1): None,
                           (-1, 0): None,
                           (-1, 1): None,
                           (0, 1): None,
                           (1, 1): None,
                           (1, 0): None,
                           (1, -1): None,
                           (0, -1): None}

        radius = 4
        spy = 12
        brush_size = self.brush_size
        rgb = [0, 0, 255]
        half_rgb = [int(color * 0.5) for color in rgb]
        center = mathutils.Vector([brush_size * 0.5, brush_size * 0.5])

        for key in directions_dict:

            brush = bytearray(brush_size * brush_size * 4)
            direction = mathutils.Vector(key)

            for x in range(brush_size):
                for y in range(brush_size):
                    i = y * (brush_size * 4) + x * 4
                    location = mathutils.Vector([x, y])
                    target_vector = location - center
                    length = target_vector.length

                    if length > 0.0:
                        angle = math.degrees(direction.angle(target_vector))
                    else:
                        angle = 0.0

                    if length > radius:
                        if length > spy:
                            pixel = [0, 0, 0]
                        else:
                            if angle < 30.0:
                                pixel = rgb
                            elif angle < 45:
                                pixel = half_rgb
                            else:
                                if length < radius + 2:
                                    pixel = half_rgb
                                else:
                                    pixel = [0, 0, 0]

                    else:
                        pixel = rgb

                    brush[i] = pixel[0]
                    brush[i + 1] = pixel[1]
                    brush[i + 2] = pixel[2]
                    brush[i + 3] = 255

            directions_dict[key] = brush

        return directions_dict

    def do_paint(self):
        player_agent_list = [agent for agent in self.manager.agents if agent.team == 0]
        enemy_agent_list = [agent for agent in self.manager.agents if
                            agent.team != 0 and agent.visible and agent.agent_type != "BUILDING"]

        for agent in player_agent_list:
            x, y = bgeutils.get_terrain_position(agent.location)
            bx = x - int(self.brush_size * 0.5)
            by = y - int(self.brush_size * 0.5)

            brush = self.spy_brushes[agent.facing]

            self.canvas.source.plot(self.vision_brush, self.brush_size, self.brush_size, bx, by,
                                    bge.texture.IMB_BLEND_LIGHTEN)
            self.canvas.source.plot(self.player_pixel, self.brush_size, self.brush_size, bx, by,
                                    bge.texture.IMB_BLEND_LIGHTEN)

        for agent in enemy_agent_list:
            x, y = bgeutils.get_terrain_position(agent.location)
            bx = x - int(self.brush_size * 0.5)
            by = y - int(self.brush_size * 0.5)
            self.canvas.source.plot(self.enemy_pixel, self.brush_size, self.brush_size, bx, by,
                                    bge.texture.IMB_BLEND_LIGHTEN)

        self.canvas.refresh(True)

    def update(self):

        if self.refresh_timer >= self.max_refresh:
            self.canvas = self.create_canvas()
            self.refresh_timer = 0
            self.do_paint()

        else:
            self.refresh_timer += 1
