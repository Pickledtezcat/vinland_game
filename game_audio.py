import bge
import aud

device = aud.device()
device.distance_model = aud.AUD_DISTANCE_MODEL_INVERSE_CLAMPED


class SoundEffect(object):
    def __init__(self, manager, handle, game_object):
        self.manager = manager
        self.handle = handle
        self.game_object = game_object
        self.handle.attenuation = 1.0

    def update(self):
        self.handle.location = self.game_object.worldPosition.copy()
        self.handle.orientation = self.game_object.worldOrientation.copy().to_quaternion()


class Audio(object):
    def __init__(self, manager):
        self.manager = manager
        self.buffered = {}
        self.sound_effects = []
        self.scene = self.manager.scene
        self.camera = self.manager.camera_object
        self.music = None

    def sound_effect(self, sound_name, game_object, loop=0, volume_scale=1.0, attenuation=None):

        sound_path = bge.logic.expandPath("//sounds/")
        file_name = "{}{}.wav".format(sound_path, sound_name)

        if sound_name not in self.buffered:
            self.buffered[sound_name] = aud.Factory.buffer(aud.Factory(file_name))

        try:
            if isinstance(game_object, bge.types.KX_GameObject):
                handle = device.play(self.buffered[sound_name])
                handle.relative = False
                handle.loop_count = int(loop)

                if not game_object.invalid:
                    sound_effect = SoundEffect(self.manager, handle, game_object)
                    self.sound_effects.append(sound_effect)

                handle.volume = bge.logic.globalDict.get('volume', 0.2) * volume_scale
                if attenuation:
                    handle.attenuation = attenuation
                return handle

        except:
            print(game_object.name, sound_name)

        return None

    def update(self):

        device.listener_location = self.camera.worldPosition.copy()
        device.listener_orientation = self.camera.worldOrientation.copy().to_quaternion()

        next_generation = []

        for sound_effect in self.sound_effects:
            if sound_effect.handle.status != aud.AUD_STATUS_INVALID:
                if sound_effect.game_object.invalid:
                    sound_effect.handle.stop()
                else:
                    sound_effect.update()
                    next_generation.append(sound_effect)

        self.sound_effects = next_generation

    def play_music(self, sound_name, vol=1.0):
        if self.music:
            self.music.stop()

        sound_path = bge.logic.expandPath("//music/")
        file_name = "{}{}.wav".format(sound_path, sound_name)

        handle = device.play(aud.Factory(file_name))
        handle.volume = vol
        handle.loop_count = -1
        self.music = handle
