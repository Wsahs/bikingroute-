"""Conservative routing on an explicitly connected, directed geographic graph."""
import heapq
import itertools
import math
from collections import defaultdict

QUARTER_MILE_M = 402.336
DETOUR_SECONDS = 900
OFFROAD = frozenset(('sidewalk', 'path', 'trail', 'crossing'))


class SearchLimitError(Exception):
    """An unfinished computation is never equivalent to no route."""


def eligible(edge):
    if edge.get('bicycle_allowed') is not True or edge.get('assessed') is not True or edge.get('closed'):
        return False
    kind = edge.get('kind')
    if kind == 'street':
        return edge.get('quiet_verified') is True
    if kind == 'crossing':
        return edge.get('designated') is True
    return kind in OFFROAD


class Network:
    def __init__(self, graph):
        self.metadata = graph.get('metadata', {})
        self.nodes = {str(n['id']): n for n in graph['nodes']}
        if len(self.nodes) != len(graph['nodes']):
            raise ValueError('Duplicate node IDs')
        self.adj = defaultdict(list)
        for edge in graph['edges']:
            length = edge.get('length_m')
            if isinstance(length, bool) or not isinstance(length, (int, float)) or not math.isfinite(length) or length <= 0:
                raise ValueError('Segment distances must be finite and positive')
            if edge['from'] not in self.nodes or edge['to'] not in self.nodes:
                raise ValueError('Segment references a missing node')
            if eligible(edge):
                self.adj[edge['from']].append(edge)


def _path(label):
    edges = []
    while label['edge'] is not None:
        edges.append(label['edge'])
        label = label['parent']
    return list(reversed(edges))


def _search(network, start, end, max_states, allow_streets=False, distance_cap=None, street_cap=None):
    """Dijkstra with Pareto labels when there is a total-distance constraint.

    At a node, a lower-street but longer label must not erase a faster label
    when the latter may be the only one that meets the detour time budget.
    Positive lengths and componentwise dominance eliminate improving cycles.
    """
    counter = itertools.count()
    first = dict(node=start, street=0.0, total=0.0, edge=None, parent=None, active=True)
    frontier = [(0.0, 0.0, next(counter), first)]
    labels = defaultdict(list, {start: [first]})
    examined = 0
    while frontier:
        _, _, _, current = heapq.heappop(frontier)
        if not current['active']:
            continue
        examined += 1
        if examined > max_states:
            raise SearchLimitError('Route search reached its computation limit. Try again; no absence of a route has been established.')
        node = current['node']
        if node == end:
            return _path(current)
        for edge in network.adj[node]:
            on_street = edge['kind'] == 'street'
            if on_street and not allow_streets:
                continue
            street = current['street'] + (edge['length_m'] if on_street else 0)
            total = current['total'] + edge['length_m']
            if street_cap is not None and street > street_cap:
                continue
            if distance_cap is not None and total > distance_cap + 1e-9:
                continue
            dest = edge['to']
            prior = labels[dest]
            if distance_cap is None:
                if any((p['street'], p['total']) <= (street, total) for p in prior):
                    continue
                for p in prior:
                    p['active'] = False
                labels[dest] = []
            else:
                if any(p['street'] <= street and p['total'] <= total for p in prior):
                    continue
                remaining = []
                for p in prior:
                    if street <= p['street'] and total <= p['total']:
                        p['active'] = False
                    else:
                        remaining.append(p)
                labels[dest] = remaining
            label = dict(node=dest, street=street, total=total, edge=edge, parent=current, active=True)
            labels[dest].append(label)
            heapq.heappush(frontier, (street, total, next(counter), label))
    return None


def _route(edges, speed):
    distance = math.fsum(e['length_m'] for e in edges)
    street = math.fsum(e['length_m'] for e in edges if e['kind'] == 'street')
    segments = []
    for edge in edges:
        # Keep whole original source segments available for disclosure.
        segments.append(dict(id=edge['id'], kind=edge['kind'], name=edge.get('name') or edge['kind'].title(),
                             distance_m=edge['length_m'], geometry=edge.get('geometry', []),
                             source=edge.get('source', ''), source_date=edge.get('source_date', 'Unknown'),
                             crossing_option=edge.get('crossing_option'), approval_required=edge.get('approval_required',False)))
    return dict(distance_m=distance, street_distance_m=street, duration_seconds=distance/speed,
                crossings=sum(e['kind'] == 'crossing' for e in edges), segments=segments)


def plan(graph, start, end, speed_mps=4.4704, max_states=200000):
    if isinstance(speed_mps, bool) or not isinstance(speed_mps, (float, int)) or not math.isfinite(speed_mps) or not 0 < speed_mps <= 20:
        raise ValueError('Cycling speed must be finite, positive and at most 20 m/s')
    network = graph if isinstance(graph, Network) else Network(graph)
    if start not in network.nodes or end not in network.nodes:
        raise ValueError('Select mapped access points for both ends')
    warnings = []
    if not network.metadata.get('coverage_complete', False):
        warnings.append('Map data is incomplete; a sidewalk/trail connection may be missing. A failed search does not prove no real-world route exists.')
    if network.metadata.get('demo'):
        warnings.append('Synthetic demonstration only. These routes are not for navigation.')
    result = dict(status='no_route', primary=None, alternative=None, requires_confirmation=False,
                  extra_seconds=None, warnings=warnings, coverage=network.metadata,
                  assumed_speed_mph=speed_mps/0.44704)
    primary_edges = _search(network, start, end, max_states)
    if primary_edges is not None:
        primary = _route(primary_edges, speed_mps)
        result.update(status='primary', primary=primary)
        cap = primary['distance_m'] - DETOUR_SECONDS * speed_mps
        if cap > 0:
            alternative_edges = _search(network, start, end, max_states, True, cap, QUARTER_MILE_M)
            if alternative_edges is not None:
                alternative = _route(alternative_edges, speed_mps)
                extra = primary['duration_seconds'] - alternative['duration_seconds']
                if alternative['street_distance_m'] > 0 and extra >= DETOUR_SECONDS - 1e-9:
                    result.update(status='confirmation', alternative=alternative,
                                  requires_confirmation=True, extra_seconds=extra)
        return result
    fallback_edges = _search(network, start, end, max_states, True)
    if fallback_edges is not None:
        result.update(status='fallback', alternative=_route(fallback_edges, speed_mps))
    elif not network.metadata.get('coverage_complete', False):
        result['status'] = 'insufficient_data'
    return result
