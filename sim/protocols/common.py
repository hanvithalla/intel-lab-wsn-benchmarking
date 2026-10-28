"""Pieces shared by the five protocol files: the state a protocol may see, the helpers
for cluster and chain plans, and the runner that carries a plan out through sim.core.

A protocol file exposes two functions:

    setup_round(state, rng) -> plan    chooses cluster heads, or the chain and its leader
    route(state)            -> hops    the (sender, receiver) pairs of that round, in the
                                       order the packets travel; receiver SINK means the sink

The protocols only ever see a `State`. It holds the sensor positions, the residual
energies, the alive flags and the round number. It does not hold the network object, so
a protocol cannot read the delivery probabilities. Everything that costs energy goes
through `execute_hops`, which calls Network.send and Network.aggregate, so all five
protocols pay through the same ledger.

Conventions that apply to every protocol (also listed in docs/protocol_choices.md):
  * Control messages (advertisements, join requests, schedules, tokens, update packets)
    are not charged, in the same way acknowledgements are not charged. Only data packets
    and data aggregation cost energy.
  * A sensor that is awake produces one reading per round. A cluster head or chain node
    fuses its own reading and every packet it received into one packet of the same size.
    Fusing k >= 2 signals costs aggregation_cost(bits, k); a node with one signal pays
    nothing to fuse.
  * If a cluster protocol ends up with no cluster head in a round, every awake sensor
    sends straight to the sink that round, and the round is counted in state.stats.
"""

import math
from collections import defaultdict

import numpy as np

from sim.core import SINK


class State:
    """What a protocol is allowed to know about the network: positions and energies."""

    def __init__(self, net, config):
        self.n = net.n
        self.pos = net.pos.copy()
        self.pos.flags.writeable = False
        self.sink = net.sink.copy()
        self.sink.flags.writeable = False
        # read-only views of the live ledger: the simulator updates them, protocols cannot
        self.energy = net.energy.view()
        self.energy.flags.writeable = False
        self.alive = net.alive.view()
        self.alive.flags.writeable = False
        self.e_init = float(net.params.e_init)
        self.packet_bits = int(net.params.packet_bits)
        self.config = dict(config)
        self.round = 0
        self.plan = None
        self.memory = {}                  # whatever the protocol wants to keep between rounds
        self.stats = defaultdict(int)     # counters the protocol reports (rounds with no head...)
        diff = self.pos[:, None, :] - self.pos[None, :, :]
        self.dmat = np.sqrt((diff ** 2).sum(axis=2))               # sensor to sensor
        self.sink_dist = np.sqrt(((self.pos - self.sink) ** 2).sum(axis=1))   # sensor to sink

    def alive_indices(self):
        return np.flatnonzero(self.alive)

    def dist(self, a, b):
        """Distance between sensors a and b; either may be SINK."""
        if a == SINK and b == SINK:
            return 0.0
        if a == SINK:
            return float(self.sink_dist[b])
        if b == SINK:
            return float(self.sink_dist[a])
        return float(self.dmat[a, b])


# ---------------------------------------------------------------- helpers for plans
def leach_epoch(p):
    """Rounds per epoch: 1/p rounded to a whole number (so p = 0.08 gives 12 rounds)."""
    return max(1, int(round(1.0 / p)))


def leach_threshold(p, round_in_epoch):
    """T(n) = p / (1 - p * (r mod 1/p)), capped at 1. `round_in_epoch` is r mod 1/p."""
    denom = 1.0 - p * round_in_epoch
    if denom <= 0.0:
        return 1.0
    return min(1.0, p / denom)


def nearest_head_assignment(state, members, heads):
    """Each member joins the nearest head (ties go to the lower sensor index)."""
    assign = {}
    if len(heads) == 0:
        for v in members:
            assign[int(v)] = SINK
        return assign
    heads = np.asarray(heads, dtype=int)
    for v in members:
        v = int(v)
        assign[v] = int(heads[int(np.argmin(state.dmat[v, heads]))])
    return assign


def cluster_plan(state, sensing, heads, assign):
    """Plan for a clustering protocol. `assign` maps every non-head sensing node to
    its head (or to SINK for a node that sends directly)."""
    return {
        "kind": "cluster",
        "sensing": [int(i) for i in sensing],
        "heads": [int(h) for h in heads],
        "assign": {int(k): int(v) for k, v in assign.items()},
        "chain": None,
        "leader": None,
    }


def plan_from_heads(state, heads):
    """Plan in which every alive sensor senses and every non-head joins the nearest head.
    With no head at all, every sensor sends straight to the sink and the round is counted."""
    sensing = state.alive_indices()
    head_set = set(int(h) for h in heads)
    if not head_set:
        state.stats["rounds_without_head"] += 1
    state.stats["heads_total"] += len(head_set)
    members = [int(v) for v in sensing if int(v) not in head_set]
    assign = nearest_head_assignment(state, members, heads)
    state.plan = cluster_plan(state, sensing, heads, assign)
    return state.plan


def cluster_route(state):
    """Hops of a cluster plan: members to their head (or to the sink) first, then every
    head to the sink."""
    plan = state.plan
    hops = [(v, plan["assign"][v]) for v in sorted(plan["assign"])]
    hops += [(h, SINK) for h in plan["heads"]]
    return hops


# ---------------------------------------------------------------- carrying a plan out
def execute_hops(net, sensing, hops):
    """Run one round's hops through the simulator.

    Every sensing node first produces one reading. Then each hop is taken in order:
    the sender fuses its own reading with what it has received (if that is two or more
    signals, it pays the aggregation cost) and sends one packet that carries all the
    readings it holds. A packet that is lost, or a node that dies on the way, loses the
    readings it held. Readings count as delivered only when a packet reaches the sink.
    """
    carried = {}
    signals = {}
    for i in sensing:
        i = int(i)
        net.generate(i)
        carried[i] = 1
        signals[i] = 1
    for src, dst in hops:
        if not net.alive[src]:
            continue
        payload = carried.get(src, 0)
        if payload <= 0:
            continue
        if signals[src] >= 2 and not net.aggregate(src, signals[src]):
            continue
        if net.send(src, dst, payload) and dst != SINK:
            carried[dst] = carried.get(dst, 0) + payload
            signals[dst] = signals.get(dst, 0) + 1
        carried[src] = 0


class ProtocolRunner:
    """Adapter that lets sim.core.run_simulation run a protocol file."""

    def __init__(self, module, config=None):
        self.module = module
        self.name = module.NAME
        self.config = {**module.DEFAULTS, **(config or {})}
        self.state = None
        self.min_energy = math.inf

    def run_round(self, net, r):
        if self.state is None:
            self.state = State(net, self.config)
        state = self.state
        state.round = r
        plan = self.module.setup_round(state, net.rng_protocol)
        hops = self.module.route(state)
        execute_hops(net, plan["sensing"], hops)
        self.min_energy = min(self.min_energy, float(net.energy.min()))

    @property
    def stats(self):
        return dict(self.state.stats) if self.state is not None else {}
