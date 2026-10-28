"""PEGASIS (Lindsey and Raghavendra, IEEE Aerospace Conference 2002, pp. 3-4 of the
hosted copy).

The chain is greedy: it starts at the sensor farthest from the sink and keeps adding the
nearest sensor that is not on it yet. The leader of round i is sensor number i mod N.
Data travels along the chain towards the leader from both ends; every sensor fuses what
it receives with its own reading into one packet, and the leader sends one packet to the
sink. The chain is rebuilt in the same way whenever a sensor has died.

There is no parameter to tune. The paper's "threshold on neighbour distance" for leaders
has no value in the paper and is left out (docs/protocol_choices.md).
"""

import numpy as np

from sim.core import SINK
from sim.protocols import common

NAME = "pegasis"
DEFAULTS = {}


def build_chain(state, alive):
    """Greedy chain over the sensors in `alive` (sorted indices)."""
    alive = [int(i) for i in alive]
    start = max(alive, key=lambda i: (state.sink_dist[i], -i))     # farthest, lowest index on a tie
    chain = [start]
    left = set(alive) - {start}
    while left:
        cand = np.array(sorted(left))
        nxt = int(cand[int(np.argmin(state.dmat[chain[-1], cand]))])   # nearest, lowest index on a tie
        chain.append(nxt)
        left.remove(nxt)
    return chain


def setup_round(state, rng):
    mem = state.memory
    alive = state.alive_indices()
    key = alive.tobytes()
    if mem.get("alive_key") != key:                 # a sensor died since the chain was built
        mem["chain"] = build_chain(state, alive) if len(alive) else []
        mem["alive_key"] = key
        state.stats["chain_builds"] += 1
    chain = mem["chain"]
    leader = int(alive[(state.round - 1) % len(alive)]) if len(alive) else None
    state.plan = {
        "kind": "chain",
        "sensing": [int(i) for i in alive],
        "heads": [leader] if leader is not None else [],
        "assign": {},
        "chain": list(chain),
        "leader": leader,
    }
    return state.plan


def route(state):
    plan = state.plan
    chain, leader = plan["chain"], plan["leader"]
    if leader is None:
        return []
    pos = chain.index(leader)
    hops = [(chain[k], chain[k + 1]) for k in range(0, pos)]                       # from the first end
    hops += [(chain[k], chain[k - 1]) for k in range(len(chain) - 1, pos, -1)]     # from the other end
    hops.append((leader, SINK))
    return hops
