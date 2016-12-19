import bge
import mathutils
import heapq
import bgeutils


class NavNode(object):
    def __init__(self, location):
        self.location = location
        self.g = 0.0
        self.f = 9000.0
        self.h = 9000.0
        self.parent = None


def create_nav_node():
    nav_node = {"g": 0.0,
                "f": 90000.0,
                "h": 90000.0,
                "parent": None}

    return nav_node


class Pathfinder(object):

    def __init__(self, agent, destination):

        self.agent = agent
        self.manager = self.agent.manager
        self.start = self.agent.location
        self.destination = destination
        self.graph = {}
        self.path = []
        self.done = False

        margin = 10

        ax, ay = self.agent.location
        dx, dy = self.destination

        self.min_x = min(ax, dx) - margin
        self.min_y = min(ay, dy) - margin

        self.max_x = max(ax, dx) + margin
        self.max_y = max(ay, dy) + margin

        self.find_path()

    def out_of_bounds(self, check_key):

        cx, cy = check_key

        if cx < self.min_x:
            return True

        if cy < self.min_y:
            return True

        if cx > self.max_x:
            return True

        if cy > self.max_x:
            return True

    def populate(self, tile_key):

        if not self.graph.get(tile_key):
            self.graph[tile_key] = NavNode(tile_key)

    def find_path(self):
        self.path = self.a_star()

    def check_blocked(self, check_key):

        ox, oy = check_key

        for cx in range(self.agent.size):
            for cy in range(self.agent.size):
                check_key = (ox + cx, oy + cy)

                check_tile = self.manager.level.get(check_key)

                if check_tile:
                        if check_tile != self.agent:
                            return True

    def heuristic(self, node):
        D = 1.0
        D2 = 1.4

        node_x, node_y = node
        goal_x, goal_y = self.destination

        dx = abs(node_x - goal_x)
        dy = abs(node_y - goal_y)
        return D * (dx + dy) + (D2 - 2 * D) * min(dx, dy)

    def a_star(self):

        current_key = self.agent.location
        self.populate(current_key)

        open_set = set()
        open_heap = []
        closed_set = set()

        path = []
        found = 0

        def path_gen(path_key):

            current = self.graph[path_key]

            final_path = []

            while current.parent:
                current = self.graph[current.parent]
                final_path.append(current.location)

            return final_path

        open_set.add(current_key)
        open_heap.append((0, current_key))

        while found == 0 and open_set:

            current_key = heapq.heappop(open_heap)[1]

            if current_key == self.destination:
                path = path_gen(current_key)
                found = 1

            open_set.remove(current_key)
            closed_set.add(current_key)

            current_node = self.graph[current_key]

            cx, cy = current_key
            search_array = [(1, 0), (1, 1), (0, 1), (1, -1), (-1, 0), (-1, 1), (0, -1), (-1, -1)]
            neighbors = [(n[0] + cx, n[1] + cy) for n in search_array]

            for neighbor_key in neighbors:

                if not self.out_of_bounds(neighbor_key) and not self.check_blocked(neighbor_key):

                    self.populate(neighbor_key)

                    n_cost = 1.0

                    if not bgeutils.diagonal(neighbor_key):
                        n_cost *= 1.4

                    if bgeutils.change_direction(current_key, neighbor_key):
                        n_cost *= 1.5

                    g_score = current_node.g + n_cost
                    relation = self.heuristic(neighbor_key)

                    if neighbor_key in closed_set and g_score >= self.graph[neighbor_key].g:
                        continue

                    if neighbor_key not in open_set or g_score < self.graph[neighbor_key].g:
                        self.graph[neighbor_key].parent = current_key
                        self.graph[neighbor_key].g = g_score

                        h_score = relation
                        f_score = g_score + h_score
                        self.graph[neighbor_key].f = f_score

                        if self.graph[neighbor_key].h > h_score:
                            self.graph[neighbor_key].h = h_score

                        if neighbor_key not in open_set:
                            open_set.add(neighbor_key)
                            heapq.heappush(open_heap, (self.graph[neighbor_key].f, neighbor_key))

        if path:
            path.reverse()
            path.pop(0)

        return path


    def a_star_x(self):

        current_key = self.agent.location

        open_set = set()
        open_heap = []
        closed_set = set()

        path = []
        found = 0

        def path_gen(path_key):

            current = self.graph[path_key]
            final_path = []

            while current.parent:
                current = self.graph[current.parent]
                final_path.append(current.location)

            return final_path

        open_set.add(current_key)
        open_heap.append((0, current_key))

        while found == 0 and open_set:

            current_key = heapq.heappop(open_heap)[1]

            if current_key == self.destination:
                path = path_gen(current_key)
                found = 1

            open_set.remove(current_key)
            closed_set.add(current_key)

            current_node = self.graph[current_key]

            cx, cy = current_key
            search_array = [(1, 0), (1, 1), (0, 1), (1, -1), (-1, 0), (-1, 1), (0, -1), (-1, -1)]
            neighbors = [(n[0] + cx, n[1] + cy) for n in search_array]
            valid_neighbors = [n_key for n_key in neighbors if not self.check_blocked(n_key)]

            for neighbor_key in valid_neighbors:

                if neighbor_key in self.graph:

                    n_cost = 1.0

                    if bgeutils.diagonal(neighbor_key):
                        n_cost *= 1.4

                    if bgeutils.change_direction(current_key, neighbor_key):
                        n_cost *= 2.0

                    g_score = current_node.g + n_cost
                    relation = self.heuristic(neighbor_key)

                    if neighbor_key in closed_set and g_score >= self.graph[neighbor_key].g:
                        continue

                    if neighbor_key not in open_set or g_score < self.graph[neighbor_key].g:
                        self.graph[neighbor_key].parent = current_key
                        self.graph[neighbor_key].g = g_score

                        h_score = relation
                        f_score = g_score + h_score
                        self.graph[neighbor_key].f = f_score

                        if self.graph[neighbor_key].h > h_score:
                            self.graph[neighbor_key].h = h_score

                        if neighbor_key not in open_set:
                            open_set.add(neighbor_key)
                            heapq.heappush(open_heap, (self.graph[neighbor_key].f, neighbor_key))

        if path:
            path.reverse()
            path.pop(0)

        return path



