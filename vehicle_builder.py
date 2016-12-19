import bge
import builder_states
import game_audio
import builder


class BuilderLoop(object):
    def __init__(self, cont):
        self.debug = True
        self.cont = cont
        self.own = cont.owner
        self.scene = self.own.scene
        self.camera_object = self.own

        self.audio = game_audio.Audio(self)

        self.mode = None
        self.chassis_size = 3
        self.turret_size = 3
        self.contents = None
        self.vehicle_stats = None
        self.faction = 1
        self.game_turn = 1
        self.selected_parts = "engine"

        starting_state = builder_states.PrepBuilder
        self.state_name = starting_state.__name__

        self.state = builder_states.PrepBuilder(self)

    def update(self):
        self.state_machine()

    def state_machine(self):
        next_state = self.state.transition()

        if next_state:
            self.state.end()
            self.state = next_state(self)
            self.state_name = next_state.__name__
        self.state.update()
