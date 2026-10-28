"""R-LEACH (Behera et al., IEEE Internet of Things Journal 2019, Eq. 4 to 6, pp. 4-5 of the
arXiv copy 1902.01445).

Round 1 uses the LEACH threshold (Eq. 4). Later rounds use Eq. 5,

    T(n) = p / (1 - p * (r mod 1/p)) * (E_residual / E_initial) * k_opt   for n in G,

capped at 1, with k_opt the optimal number of clusters (Eq. 6). Members join the nearest
head, heads fuse and send straight to the sink. Everything else is as in leach.py.

Eq. 6 as printed has a negative radicand for every distance below about 52 m, which is
all of them here, so k_opt is computed from the free-space form of the derivation the
equation comes from (docs/protocol_choices.md, R-LEACH entries).
"""

import math

import numpy as np

from sim import core
from sim.protocols import common

NAME = "rleach"
DEFAULTS = {"p": 0.05, "k_opt": None}     # k_opt None means: compute it each round


def optimal_clusters(state):
    """Optimal number of clusters for the sensors still alive.

    Heinzelman et al. (TWC 2002, Eq. 19 and its free-space version): the energy of one
    round is smallest for k = sqrt(n / 2 pi) * M / d_toBS when the heads reach the sink
    in the d^2 regime, and k = sqrt(n / 2 pi) * sqrt(eps_fs / eps_mp) * M / d_toBS^2
    when they reach it in the d^4 regime. M is the side of a square with the area of
    the box around all sensors and d_toBS the root mean square distance to the sink.
    The result is kept between 1 and n.
    """
    alive = state.alive_indices()
    n = len(alive)
    if n == 0:
        return 1.0
    mins = state.pos.min(axis=0)
    maxs = state.pos.max(axis=0)
    m_side = math.sqrt(max((maxs[0] - mins[0]) * (maxs[1] - mins[1]), 1e-12))
    d = math.sqrt(float(np.mean(state.sink_dist[alive] ** 2)))
    if d < core.D0:
        k = math.sqrt(n / (2.0 * math.pi)) * m_side / d
    else:
        k = math.sqrt(n / (2.0 * math.pi)) * math.sqrt(core.EFS / core.EMP) * m_side / (d * d)
    return float(min(max(k, 1.0), n))


def setup_round(state, rng):
    p = state.config["p"]
    epoch = common.leach_epoch(p)
    r0 = state.round - 1
    mem = state.memory
    if "in_g" not in mem:
        mem["in_g"] = np.ones(state.n, dtype=bool)
    if r0 % epoch == 0:
        mem["in_g"][:] = True
    base = common.leach_threshold(p, r0 % epoch)
    if state.round == 1:
        threshold = np.full(state.n, base)                    # Eq. 4 in the first round
    else:
        k = state.config["k_opt"]
        if k is None:
            k = optimal_clusters(state)
        threshold = np.minimum(1.0, base * (state.energy / state.e_init) * k)   # Eq. 5
        state.stats["k_opt_sum"] += k
    draws = rng.random(state.n)
    heads = np.flatnonzero(mem["in_g"] & state.alive & (draws < threshold))
    mem["in_g"][heads] = False
    return common.plan_from_heads(state, heads)


def route(state):
    return common.cluster_route(state)
