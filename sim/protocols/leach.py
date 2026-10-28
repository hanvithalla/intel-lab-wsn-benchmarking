"""LEACH (Heinzelman, Chandrakasan and Balakrishnan, HICSS 2000, p. 8).

Every round each sensor draws a random number and becomes a cluster head if it is below

    T(n) = p / (1 - p * (r mod 1/p))   for n in G, 0 otherwise,

where G holds the sensors that have not been a head in the current epoch of 1/p rounds.
Members join the nearest head, heads fuse and send straight to the sink.

Choices the paper leaves open are in docs/protocol_choices.md (epoch handling, rounds
with no head, ties).
"""

import numpy as np

from sim.protocols import common

NAME = "leach"
DEFAULTS = {"p": 0.05}


def setup_round(state, rng):
    p = state.config["p"]
    epoch = common.leach_epoch(p)
    r0 = state.round - 1                      # the paper counts rounds from 0
    mem = state.memory
    if "in_g" not in mem:
        mem["in_g"] = np.ones(state.n, dtype=bool)
    if r0 % epoch == 0:
        mem["in_g"][:] = True                 # a new epoch: every sensor may serve again
    threshold = common.leach_threshold(p, r0 % epoch)
    draws = rng.random(state.n)               # one draw per sensor, alive or not
    alive = state.alive
    heads = np.flatnonzero(mem["in_g"] & alive & (draws < threshold))
    mem["in_g"][heads] = False
    return common.plan_from_heads(state, heads)


def route(state):
    return common.cluster_route(state)
