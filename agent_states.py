
import bgeutils
import bge
import random
import math

from mathutils import Vector, Matrix
import agent_actions


class State(object):
    def __init__(self, agent):
        self.agent = agent
        self.transition_state = None
        self.debug_message = ""

        # set debug messages in the state, not the agent!!!

    def end(self):
        pass

    def transition(self):

        if self.transition_state:
            return self.transition_state

    def exit_check(self):
        return None

    def update(self):

        exit_check = self.exit_check()

        if exit_check:
            self.transition_state = exit_check
        else:
            self.process()

    def process(self):
        self.debug_message = str("{}").format(self.agent.state_name)


class AgentState(State):
    def __init__(self, agent):

        """use this for over riding agent behaviour"""

        super().__init__(agent)

    def process(self):
        super().process()


class VehicleState(AgentState):
    def __init__(self, agent):

        """use this for over riding vehicle behaviour"""

        super().__init__(agent)
        self.agent.movement = None
        self.agent.moving = False
        self.agent.throttle_target = 0.0

    def update(self):

        self.agent.animation.update()

        if self.agent.movement:
            self.agent.movement.update()

            if self.agent.movement.done:
                self.agent.movement = None

        self.agent.combat_control.update()

        self.agent.update_dynamic_stats()
        cam = self.agent.manager.camera.main_camera
        center = self.agent.box.worldPosition.copy()
        radius = self.agent.size * 2.0

        self.agent.on_screen = False

        if self.agent.visible:
            if cam.sphereInsideFrustum(center, radius) != cam.OUTSIDE:
                self.agent.on_screen = True

        super().update()

    def process(self):

        """use this for over riding vehicle actions"""

        super().process()

        self.debug_message = "*" #str("{}").format(self.agent.combat_control.target)


class VehicleStartUp(VehicleState):

    def __init__(self, agent):
        super().__init__(agent)
        self.agent.load_vehicle()
        self.agent.combat_control = agent_actions.VehicleCombatControl(self.agent)
        self.agent.set_position()
        self.agent.animation = agent_actions.AgentAnimation(self.agent, True)

    def exit_check(self):
        if self.agent.team != 0:
            return VehicleMovingAI

        return VehicleIdle


class VehicleShooting(VehicleState):

    def __init__(self, agent):
        super().__init__(agent)
        self.agent.animation.survey_points()

        self.agent.movement = agent_actions.AgentEnemyTargeter(self.agent)

    def exit_check(self):

        if self.agent.destinations:
            return VehicleMoving

        if self.agent.rotation_target:
            return VehicleRotation

        if not self.agent.enemy_target.visible:
            self.agent.enemy_target = None
            return VehicleIdle

        if not self.agent.enemy_target:
            return VehicleIdle

    def process(self):
        super().process()

        if not self.agent.movement:
            self.agent.movement = agent_actions.AgentEnemyTargeter(self.agent)


class VehicleIdle(VehicleState):

    def __init__(self, agent):
        super().__init__(agent)
        self.agent.animation.survey_points()
        self.agent.movement = agent_actions.AgentTargeter(self.agent)

    def exit_check(self):
        if self.agent.enemy_target:
            return VehicleShooting

        if self.agent.destinations:
            return VehicleMoving

        if self.agent.rotation_target:
            return VehicleRotation

    def process(self):
        super().process()


class VehicleRotation(VehicleState):

    def __init__(self, agent):
        super().__init__(agent)

        self.agent.get_facing()

        self.agent.movement = agent_actions.AgentTargeter(self.agent)
        self.agent.rotation_target = None

    def exit_check(self):
        if self.agent.enemy_target:
            return VehicleShooting

        if self.agent.destinations:
            return VehicleMoving

        if self.agent.rotation_target:
            return VehicleRotation

        if not self.agent.movement:
            return VehicleIdle

    def process(self):
        super().process()


class VehicleMoving(VehicleState):

    def __init__(self, agent):
        super().__init__(agent)

        self.agent.stop_movement = False

        if self.agent.destinations:
            destination = self.agent.destinations.pop(0)
            self.pathfinder = agent_actions.AgentPathfinding(self.agent, destination)

        else:
            self.pathfinder = None

        self.agent.movement = agent_actions.AgentTargeter(self.agent)

    def exit_check(self):

        if not self.pathfinder:
            if self.agent.rotation_target:
                return VehicleRotation
            if self.agent.destinations:
                return VehicleMoving
            else:
                return VehicleIdle

    def process(self):
        super().process()

        if self.pathfinder:
            self.pathfinder.update()

            if self.pathfinder.done:
                self.pathfinder = None


class VehicleMovingAI(VehicleMoving):

    def __init__(self, agent):
        super().__init__(agent)

        destination = self.agent.manager.waypoints.point_list[self.agent.waypoint].location
        self.pathfinder = agent_actions.AgentPathfinding(self.agent, destination)

    def exit_check(self):

        if not self.pathfinder:
            if self.agent.waypoint >= len(self.agent.manager.waypoints.point_list) - 1:
                self.agent.waypoint = 0
            else:
                self.agent.waypoint += 1

            return VehicleMovingAI


class InfantryState(AgentState):
    def __init__(self, agent):

        """use this for over riding infantry behaviour"""

        super().__init__(agent)
        self.agent.movement = None
        self.agent.moving = False

        self.agent.avoid_radius = 3

    def update(self):

        self.agent.animation.update()
        self.agent.process_squad()

        if self.agent.movement:
            self.agent.movement.update()

            if self.agent.movement.done:
                self.agent.movement = None

        self.agent.combat_control.update()

        cam = self.agent.manager.camera.main_camera
        center = self.agent.box.worldPosition.copy()
        radius = self.agent.size * 2.0

        self.agent.on_screen = False

        if self.agent.visible:
            if cam.sphereInsideFrustum(center, radius) != cam.OUTSIDE:
                self.agent.on_screen = True

        super().update()

    def process(self):

        """use this for over riding infantry actions"""

        super().process()

        #self.debug_message = self.agent.load_name

        if self.agent.team == 0:
            if self.agent.selected:
                self.agent.flag.visible = True
            else:
                self.agent.flag.visible = False

        else:
            self.agent.flag.visible = False


class InfantryStartup(InfantryState):
    def __init__(self, agent):
        super().__init__(agent)
        self.agent.set_position()
        self.agent.animation = agent_actions.AgentAnimation(self.agent, False)
        self.agent.combat_control = agent_actions.InfantryCombatControl(self.agent)

    def exit_check(self):
        return InfantryIdle


class InfantryIdle(InfantryState):
    def __init__(self, agent):
        super().__init__(agent)

        self.agent.avoid_radius = 12
        self.agent.animation.survey_points()
        self.agent.movement = agent_actions.AgentTargeter(self.agent)

    def exit_check(self):
        if self.agent.enemy_target:
            return InfantryShooting

        if self.agent.rotation_target:
            return InfantryRotation

        if self.agent.destinations:
            return InfantryMoving

    def process(self):
        super().process()


class InfantryRotation(InfantryState):

    def __init__(self, agent):
        super().__init__(agent)

        self.agent.get_facing()

        self.agent.movement = agent_actions.AgentTargeter(self.agent)
        self.agent.rotation_target = None

    def exit_check(self):

        if self.agent.enemy_target:
            return InfantryShooting

        if self.agent.destinations:
            return InfantryMoving

        if self.agent.rotation_target:
            return InfantryRotation

        if not self.agent.movement:
            return InfantryIdle

    def process(self):
        super().process()


class InfantryShooting(InfantryState):

    def __init__(self, agent):
        super().__init__(agent)
        self.agent.animation.survey_points()
        self.agent.movement = agent_actions.AgentEnemyTargeter(self.agent)

    def exit_check(self):

        if self.agent.destinations:
            return InfantryMoving

        if self.agent.rotation_target:
            return InfantryRotation

        if not self.agent.enemy_target.visible:
            self.agent.enemy_target = None
            return InfantryIdle

        if not self.agent.enemy_target:
            return InfantryIdle

    def process(self):
        super().process()

        if not self.agent.movement:
            self.agent.movement = agent_actions.AgentEnemyTargeter(self.agent)


class InfantryMoving(InfantryState):

    def __init__(self, agent):
        super().__init__(agent)

        self.agent.stop_movement = False

        if self.agent.destinations:
            destination = self.agent.destinations.pop(0)
            self.pathfinder = agent_actions.AgentPathfinding(self.agent, destination)

        else:
            self.pathfinder = None

        self.agent.movement = agent_actions.AgentTargeter(self.agent)

    def exit_check(self):

        if not self.pathfinder:
            if self.agent.rotation_target:
                return InfantryRotation

            if self.agent.destinations:
                return InfantryMoving
            else:
                return InfantryIdle

    def process(self):
        super().process()

        if self.pathfinder:

            self.pathfinder.update()

            if self.pathfinder.done:
                self.pathfinder = None
