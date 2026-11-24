"""Find roads in the background ground that reconnect the existing detailed network."""

from collections import defaultdict, deque

from shapely.geometry import LineString, Point


def _blocks(graph):
    """Yield biconnected edge sets, including bridges as one-edge sets."""
    visits, low = {}, {}
    edges = []
    for root in graph:
        if root in visits:
            continue
        visits[root] = low[root] = len(visits)
        stack = [(root, None, iter(graph[root]))]
        while stack:
            node, parent_edge, neighbours = stack[-1]
            item = next(neighbours, None)
            if item is None:
                stack.pop()
                if parent_edge is not None:
                    parent = stack[-1][0]
                    low[parent] = min(low[parent], low[node])
                    if low[node] >= visits[parent]:
                        block = []
                        while edges:
                            edge = edges.pop()
                            block.append(edge)
                            if edge == parent_edge:
                                break
                        yield block
                continue
            to, edge = item
            if edge == parent_edge:
                continue
            if to not in visits:
                visits[to] = low[to] = len(visits)
                edges.append(edge)
                stack.append((to, edge, iter(graph[to])))
            elif visits[to] < visits[node]:
                low[node] = min(low[node], visits[to])
                edges.append(edge)


def _links_between_anchors(graph, endpoints, anchors):
    # Remove terminal branches of the block-cut forest unless they lead to a detailed road.
    blocks = list(_blocks(graph))
    forest = defaultdict(set)
    for i, block in enumerate(blocks):
        for key in {vertex for edge in block for vertex in endpoints[edge]}:
            forest[i].add(key)
            forest[key].add(i)
    queue = deque(key for key, branches in forest.items() if len(branches) <= 1 and key not in anchors)
    while queue:
        key = queue.popleft()
        for neighbour in forest.pop(key, ()):
            forest[neighbour].discard(key)
            if len(forest[neighbour]) == 1 and neighbour not in anchors:
                queue.append(neighbour)
    return [edge for i, block in enumerate(blocks) if len(forest.get(i, ())) >= 2 for edge in block]


def find_connectors(net, detailed, fill):
    """Return reconnecting road edge IDs and their outside centreline length."""
    boundary = detailed.boundary
    endpoints, segments = [], []
    graph = defaultdict(list)
    anchors = set()
    for edge in net.edges:
        line = LineString(edge.P[:, :2])
        if not line.intersects(fill):
            continue
        outside = line.intersection(fill).difference(detailed)
        parts = getattr(outside, "geoms", (outside,))
        reaches_detailed = line.intersection(detailed).length > 2.0
        for part in parts:
            if part.geom_type != "LineString" or part.length < 1.0:
                continue
            coordinates = [Point(part.coords[i]) for i in (0, -1)]
            keys = []
            for i, point in enumerate(coordinates):
                if point.distance(Point(line.coords[0])) <= 1e-5:
                    key = ("node", edge.a)
                elif point.distance(Point(line.coords[-1])) <= 1e-5:
                    key = ("node", edge.b)
                else:
                    key = ("cut", len(endpoints), i)
                if reaches_detailed and point.distance(boundary) <= 1e-5:
                    anchors.add(key)
                keys.append(key)
            a, b = keys
            if a == b:
                continue
            index = len(endpoints)
            endpoints.append((a, b))
            segments.append((edge, part))
            graph[a].append((b, index))
            graph[b].append((a, index))
    selected = [segments[i] for i in _links_between_anchors(graph, endpoints, anchors)]
    return {edge.id for edge, _ in selected}, sum(part.length for _, part in selected)
