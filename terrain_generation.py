import bge
import random
import bgeutils


def set_wall(target):
    if random.randint(0, 100) > target:
        return 1

    return 0


def automata(level_dict, max_size, fill_holes=False):
    new_dict = {(x, y): level_dict.get((x, y), 0) for x in range(max_size) for y in range(max_size)}

    for tile_key in level_dict:

        neighbors = [(x, y) for x in range(-1, 2) for y in range(-1, 2)]

        count = 0
        x, y = tile_key

        for n in neighbors:
            n_key = (x + n[0], y + n[1])
            n_tile = level_dict.get(n_key, 0)
            count += n_tile

        if fill_holes:
            is_wall = int(count > 4) or int(count < 1)
        else:
            is_wall = int(count > 4)

        if is_wall:
            home_tile = 1
        else:
            home_tile = 0

        new_dict[tile_key] = home_tile

    return new_dict


class TerrainGeneration(object):
    def __init__(self, manager, ground_object):
        self.manager = manager
        self.ground_object = ground_object
        self.canvas_size = 64
        self.canvas = self.create_canvas()
        self.field = self.generate_field()

        self.canvas.refresh(False)

    def create_canvas(self):
        canvas_size = self.canvas_size

        tex = bge.texture.Texture(self.ground_object, 0, 0)
        tex.source = bge.texture.ImageBuff(color=0)

        tex.source.load(b'\x00\x00\x00' * (canvas_size * canvas_size), canvas_size, canvas_size)

        return tex

    def create_pixel(self, r, g, b, a):
        pixel = bytearray(1 * 1 * 4)
        pixel[0] = r
        pixel[1] = g
        pixel[2] = b
        pixel[3] = a

        return pixel

    def generate_field(self):

        max_size = self.canvas_size

        field = {(x, y): set_wall(45) for x in range(-1, max_size) for y in range(-1, max_size)}

        field = automata(field, max_size, fill_holes=True)
        field = automata(field, max_size, fill_holes=True)
        field = automata(field, max_size, fill_holes=True)

        road = [(x, 13) for x in range(1, 64)]

        for key in field:
            x, y = key
            value = int(field[key] * 255)

            road_color = 0
            if (x, y) in road:
                road_color = 255

            pixel = self.create_pixel(value, 0, road_color, 255)
            self.canvas.source.plot(pixel, 1, 1, x, y, 0)

        for x in range(1, 64):
            y = 12

            pixel = self.create_pixel(value, 0, 0, 255)
            self.canvas.source.plot(pixel, 1, 1, x, y, 0)

        return field
