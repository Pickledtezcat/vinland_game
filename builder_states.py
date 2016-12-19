import bge
import mathutils
import random
import builder
import model_display


class BuilderState(object):
    def __init__(self, manager):
        self.manager = manager
        self.transition_state = None

    def end(self):
        pass

    def transition(self):
        return self.transition_state

    def update(self):
        pass
        self.manager.audio.update()
        """add audio update here, audio should be updated for all gamestates
        """


class PrepBuilder(BuilderState):
    def __init__(self, manager):
        super().__init__(manager)

        bge.render.setMipmapping(2)
        bge.render.setAnisotropicFiltering(2)

        tile_path_path = bge.logic.expandPath("//models/vehicles.blend")
        bge.logic.LibLoad(tile_path_path, "Scene")

        """lib load here and any other things which need to be done before startup
        """

    def update(self):
        super().update()

        if self.manager.debug:
            self.transition_state = DebugVehicleBuilder


class DebugVehicleBuilder(BuilderState):
    def __init__(self, manager):
        super().__init__(manager)

        self.manager.mode = builder.DebugBuilderMode(self.manager)

    def update(self):
        mode_change = self.manager.mode.process_mode()

        if mode_change:
            self.transition_state = globals()[mode_change]


class VehicleExit(BuilderState):
    def __init__(self, manager):
        super().__init__(manager)

        self.manager.mode = builder.ExitMode(self.manager)

    def update(self):
        mode_change = self.manager.mode.process_mode()

        if mode_change:
            self.transition_state = globals()[mode_change]


class VehicleSave(BuilderState):
    def __init__(self, manager):
        super().__init__(manager)

        self.manager.mode = builder.SaveMode(self.manager)

    def update(self):
        mode_change = self.manager.mode.process_mode()

        if mode_change:
            self.transition_state = globals()[mode_change]


class VehicleCheck(BuilderState):
    def __init__(self, manager):
        super().__init__(manager)

        self.manager.mode = builder.DisplayMode(self.manager)

    def update(self):
        mode_change = self.manager.mode.process_mode()

        if mode_change:
            self.transition_state = globals()[mode_change]







