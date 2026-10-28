"""ECH, the Enhanced Clustering Hierarchy (El Alami and Najid, IEEE Access 7, 2019,
Section III and Algorithms 1 and 2, pp. 107146-107148).

Each round has four steps.

1. Groups. Two sensors are neighbours if they are within 2 * R_sense of each other (Eq. 10).
   A sensor with no neighbour is unpaired and stays awake.
2. Sleeping and waking (Algorithm 1). Sensors decide one at a time, smallest weight first;
   a sensor goes to sleep if its sensing disk of radius R_sense is fully covered by the
   sensing disks of neighbours that have already announced WAKING, otherwise it announces
   WAKING. Sleeping sensors sense, compute and transmit nothing and spend nothing.
3. Cluster heads. The waking and unpaired sensors draw a random number against a LEACH
   threshold Th built from p_opt = k_opt / n_active (Eq. 23 and 24). If there are too few
   candidates, far-away normal sensors may draw again; if there are too many, the candidates
   with the lowest "chance" go back to being normal sensors (Algorithm 2).
4. Data. A normal sensor sends straight to the sink if the sink is nearer than every head
   (it would hear the sink most strongly), otherwise it joins the nearest head. Heads fuse
   and send straight to the sink.

The study calls R_sense the overlap radius and tunes it over 2, 4, 6 and 8 m. Every detail
the paper leaves unstated is in docs/protocol_choices.md.
"""

import math

import numpy as np

from sim.core import SINK
from sim.protocols import common

NAME = "ech"
DEFAULTS = {"overlap_radius": 8.0}

K_OPT_FACTOR = 2.0 / (2.0 * math.pi * 0.765)        # k_opt^2 = K_OPT_FACTOR * n_active  (Eq. 23)


def sample_offsets():
    """Points of a sensing disk of radius 1: the centre, 8 points at 1/2 and 16 at 1."""
    pts = [(0.0, 0.0)]
    for radius, count in ((0.5, 8), (1.0, 16)):
        for k in range(count):
            a = 2.0 * math.pi * k / count
            pts.append((radius * math.cos(a), radius * math.sin(a)))
    return np.array(pts)


OFFSETS = sample_offsets()


def fully_monitored(centre, neighbours, radius):
    """True if every sample point of the sensing disk at `centre` lies within `radius` of
    some awake neighbour (`neighbours` is an array of positions)."""
    if len(neighbours) == 0:
        return False
    pts = centre + radius * OFFSETS
    d2 = ((pts[:, None, :] - neighbours[None, :, :]) ** 2).sum(axis=2)
    return bool((d2 <= radius * radius + 1e-9).any(axis=1).all())


def choose_awake(state, alive, radius):
    """Algorithm 1. Returns (awake mask over all sensors, number of unpaired sensors)."""
    awake = np.zeros(state.n, dtype=bool)
    order = sorted(alive, key=lambda i: (-state.energy[i], i))    # weight R/E: most energy decides first
    alive_mask = state.alive
    unpaired = 0
    for i in order:
        near = np.flatnonzero((state.dmat[i] <= 2.0 * radius) & alive_mask)
        near = near[near != i]
        if len(near) == 0:
            awake[i] = True                                       # unpaired: always awake
            unpaired += 1
            continue
        waking = near[awake[near]]
        if not fully_monitored(state.pos[i], state.pos[waking], radius):
            awake[i] = True                                       # broadcasts WAKING
    return awake, unpaired


def setup_round(state, rng):
    radius = state.config["overlap_radius"]
    alive = state.alive_indices()
    mem = state.memory
    if "last_head" not in mem:
        mem["last_head"] = np.full(state.n, -10 ** 9, dtype=np.int64)
    draw_first = rng.random(state.n)
    draw_second = rng.random(state.n)
    if len(alive) == 0:
        state.plan = common.cluster_plan(state, [], [], {})
        return state.plan

    awake, unpaired = choose_awake(state, alive, radius)
    active = np.flatnonzero(awake)
    state.stats["asleep_node_rounds"] += len(alive) - len(active)
    state.stats["unpaired_node_rounds"] += unpaired

    n_act = len(active)
    k_opt = math.sqrt(K_OPT_FACTOR * n_act)                       # Eq. 23
    p_opt = min(1.0, k_opt / n_act)                               # Eq. 24
    epoch = common.leach_epoch(p_opt)
    threshold = common.leach_threshold(p_opt, (state.round - 1) % epoch)
    may_serve = (state.round - mem["last_head"]) >= epoch         # not a head in the last rounds
    target = max(1, int(round(k_opt)))

    candidates = [int(v) for v in active if may_serve[v] and draw_first[v] <= threshold]

    if len(candidates) < target:                                  # case 2: re-election
        cset = set(candidates)
        for v in active:
            v = int(v)
            if v in cset or not may_serve[v]:
                continue
            far = (not candidates) or state.dmat[v, candidates].mean() > state.sink_dist[v]
            if far and draw_second[v] <= threshold:
                candidates.append(v)
        state.stats["reelections"] += 1

    while len(candidates) > target:                               # case 3: Algorithm 2
        c = np.array(candidates)
        energy = state.energy[c]
        local = state.dmat[np.ix_(c, c)].sum(axis=1)              # Eq. 25, sum of distances
        e_part = energy / energy.max() if energy.max() > 0 else np.zeros(len(c))
        d_part = 1.0 - local / local.max() if local.max() > 0 else np.ones(len(c))
        chance = 0.5 * e_part + 0.5 * d_part
        candidates.pop(int(np.argmin(chance)))                    # lowest chance goes back
        state.stats["head_removals"] += 1

    heads = sorted(candidates)
    for h in heads:
        mem["last_head"][h] = state.round
    if not heads:
        state.stats["rounds_without_head"] += 1
    state.stats["heads_total"] += len(heads)

    head_set = set(heads)
    members = [int(v) for v in active if int(v) not in head_set]
    assign = {}
    for v in members:
        if not heads:
            assign[v] = SINK
            continue
        nearest = int(np.array(heads)[int(np.argmin(state.dmat[v, heads]))])
        assign[v] = SINK if state.sink_dist[v] < state.dmat[v, nearest] else nearest
    state.plan = common.cluster_plan(state, active, heads, assign)
    return state.plan


def route(state):
    return common.cluster_route(state)
