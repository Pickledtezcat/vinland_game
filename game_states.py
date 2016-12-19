
import bgeutils
import bge
from mathutils import Vector, Matrix
import random


class GameState(object):
    def __init__(self, manager):
        self.manager = manager
        self.transition_state = None

    def end(self):
        pass

    def transition(self):
        return self.transition_state

    def update(self):
        pass
        """add audio update here, audio should be updated for all gamestates
        """


class PrepGame(GameState):
    def __init__(self, manager):
        super().__init__(manager)

        """
        lib load here and any other things which need to be done before startup
        """

        self.manager.profile("prep_level", one_time=True)

    def update(self):
        super().update()

        self.transition_state = StartUp


class StartUp(GameState):
    def __init__(self, manager):
        super().__init__(manager)

        """
        load map and agents here
        """
        self.manager.profile("start_up", one_time=True)

    def update(self):
        super().update()

        self.transition_state = RunningState


class ActiveState(GameState):
    def __init__(self, manager):
        super().__init__(manager)

        """use this to give running state behavior to all running stats
        """

    def update(self):
        super().update()

        if "pause" in self.manager.input.keys:
            self.manager.paused = not self.manager.paused

        self.manager.profile("general_control")


class RunningState(ActiveState):
    def __init__(self, manager):
        super().__init__(manager)

        self.timer = 1.1

    def update(self):
        super().update()

        self.manager.profile("get_cursor_location")
        self.manager.profile("agent_control")
        self.manager.profile("agent_commands")
        self.manager.profile("agents_update")
        self.manager.profile("particle_update")
        self.manager.profile("particle_light_update")

        if self.manager.console:
            if self.timer > 1.0:
                self.timer = 0.0
                timer = self.manager.debug_timer
                times = [timer[key] for key in timer]
                times.append("number of particles:{}".format(str(len(self.manager.particles))))
                self.manager.debug_message = "\n".join(times)
            else:
                self.timer += 0.01

        else:
            self.manager.debug_message =""


# UI states


class UISetUp(GameState):
    def __init__(self, manager):
        super().__init__(manager)

        """use this to set up the UI, load buttons etc...
        """

    def update(self):
        super().update()

        self.transition_state = UIRunningState


class UIActiveState(GameState):
    def __init__(self, manager):
        super().__init__(manager)

        """the main UI state use this to update all running states for UI
        remember to change cursor to menu cursor update for menu states
        """

    def update(self):
        super().update()

        self.manager.profile("game_cursor_update")
        self.manager.profile("draw_selection_box")


class UIRunningState(UIActiveState):
    def __init__(self, manager):
        super().__init__(manager)

        """normal game play state
        """

    def update(self):
        super().update()
