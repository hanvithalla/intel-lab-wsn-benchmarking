"""Shared round-based simulator core: node state, energy ledger and link layer.

Every protocol (LEACH, HEED, PEGASIS, R-LEACH, ECH) runs on this one core, so
all five pay for energy through the same three functions and the same charge
method. Nothing in this file knows about any particular protocol.

Radio model: the first-order model of Heinzelman, Chandrakasan and Balakrishnan,
IEEE Trans. Wireless Communications 1(4), 2002, Eq. 9 and 10.

    E_Tx(l, d) = l*E_elec + l*eps_fs*d^2     for d <  d0
               = l*E_elec + l*eps_mp*d^4     for d >= d0,   d0 = sqrt(eps_fs/eps_mp)
    E_Rx(l)    = l*E_elec
    E_DA       = 5 nJ/bit/signal for aggregation at a cluster head

Conventions (these are the choices the papers leave open; they apply to every protocol):
  * Sensors are numbered 0..n-1. The sink is the constant SINK (-1). The sink has
    unlimited energy and is never charged.
  * Link layer. In "ideal" mode a hop is one attempt that always succeeds. In
    "measured" mode each attempt succeeds with the probability for that sender and
    receiver, up to max_attempts (8) attempts. Every attempt charges transmit energy
    to the sender and receive energy to a sensor receiver. Acknowledgements are not
    charged in either mode.
  * A charge that a node cannot afford kills the node: its remaining energy is used
    up and the operation does not happen. A node is dead when its energy reaches 0.
    A dead node cannot send or receive. Energy is never negative.
  * Packets. Every reading is one packet_bits packet. Aggregation fuses readings into
    one packet of the same length. "packets_generated" counts readings produced and
    "packets_delivered" counts readings that reach the sink inside a delivered packet,
    so a fused packet carrying k readings counts k. This keeps the packet delivery
    ratio comparable across protocols that fuse differently.
  * aggregation_cost(bits, n_signals) charges E_DA per bit for every signal fused, so
    the caller says how many signals are fused (including the cluster head's own
    reading, as in Eq. 11 of the TWC paper, if it fuses its own).
  * Two independent random streams come from one seed: net.rng_link (which link
    attempts succeed) and net.rng_protocol (available to protocols for their random
    choices). A protocol that uses more random numbers therefore cannot change the
    link outcomes of another.
"""

import csv
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- constants
E_ELEC = 50e-9        # J/bit, transmitter or receiver electronics
EFS = 10e-12          # J/bit/m^2, free-space amplifier
EMP = 0.0013e-12      # J/bit/m^4, multipath amplifier
D0 = math.sqrt(EFS / EMP)   # crossover distance, about 87.7 m
E_DA = 5e-9           # J/bit/signal, data aggregation at a cluster head

E_INIT = 0.5          # J per sensor at the start
PACKET_BITS = 4000    # bits per data packet
MAX_ATTEMPTS = 8      # attempts per hop in measured mode
ROUND_CAP = 20000     # a run stops here if some sensor is still alive

SINK = -1             # index used for the sink in send() and dist()


# ---------------------------------------------------------------- energy model
def radio_cost(bits, distance):
    """Energy in J to transmit `bits` over `distance` metres (first-order model)."""
    if bits < 0 or distance < 0:
        raise ValueError("bits and distance must be non-negative")
    if distance < D0:
        return bits * (E_ELEC + EFS * distance * distance)
    return bits * (E_ELEC + EMP * distance ** 4)


def rx_cost(bits):
    """Energy in J to receive `bits`."""
    if bits < 0:
        raise ValueError("bits must be non-negative")
    return bits * E_ELEC


def aggregation_cost(bits, n_signals):
    """Energy in J to aggregate `n_signals` signals of `bits` bits each."""
    if bits < 0 or n_signals < 0:
        raise ValueError("bits and n_signals must be non-negative")
    return E_DA * bits * n_signals


# ---------------------------------------------------------------- configuration
@dataclass(frozen=True)
class Params:
    e_init: float = E_INIT
    packet_bits: int = PACKET_BITS
    max_attempts: int = MAX_ATTEMPTS
    round_cap: int = ROUND_CAP


# ---------------------------------------------------------------- network
class Network:
    """Node state, energy ledger and link layer for one run."""

    def __init__(self, positions, sink, link_mode="ideal", prob=None, params=None, seed=0):
        self.pos = np.asarray(positions, dtype=float).reshape(-1, 2)
        self.sink = np.asarray(sink, dtype=float).reshape(2)
        self.n = len(self.pos)
        self.params = params or Params()
        if link_mode not in ("ideal", "measured"):
            raise ValueError("link_mode must be 'ideal' or 'measured'")
        self.link_mode = link_mode
        if link_mode == "measured":
            prob = np.asarray(prob, dtype=float)
            if prob.shape != (self.n + 1, self.n + 1):
                raise ValueError("prob must be (n+1) x (n+1), with the sink as the last index")
        self.prob = prob
        self.seed = seed
        self.meta = {}
        seq = np.random.SeedSequence(seed)
        link_seq, proto_seq = seq.spawn(2)
        self.rng_link = np.random.default_rng(link_seq)
        self.rng_protocol = np.random.default_rng(proto_seq)

        self.energy = np.full(self.n, self.params.e_init, dtype=float)
        self.alive = np.ones(self.n, dtype=bool)
        self.death_round = np.full(self.n, -1, dtype=int)
        self.current_round = 0

        # per-round counters (reset by begin_round)
        self.round_energy_spent = 0.0
        self.round_generated = 0
        self.round_delivered = 0
        # whole-run totals
        self.total_energy_spent = 0.0
        self.spent_tx = 0.0
        self.spent_rx = 0.0
        self.spent_agg = 0.0
        self.total_generated = 0
        self.total_delivered = 0
        self.attempts_total = 0
        self.hops_attempted = 0
        self.hops_delivered = 0

    # ---- loading -------------------------------------------------------------
    @classmethod
    def from_layout_file(cls, path, params=None, seed=0):
        """A random layout (data/layouts/*.json): ideal links."""
        with open(path) as f:
            layout = json.load(f)
        net = cls(layout["sensors"], layout["sink"], "ideal", None, params, seed)
        net.meta = {"deployment": layout["deployment"], "layout_seed": layout["seed"]}
        return net

    @classmethod
    def from_intel_file(cls, path, link_mode="ideal", params=None, seed=0):
        """The Intel deployment (data/intel.json), with ideal or measured links."""
        with open(path) as f:
            intel = json.load(f)
        positions = [[s["x"], s["y"]] for s in intel["sensors"]]
        sink = [intel["sink"]["x"], intel["sink"]["y"]]
        n = len(positions)
        prob = None
        if link_mode == "measured":
            prob = np.zeros((n + 1, n + 1))
            prob[:n, :n] = np.asarray(intel["prob_matrix"], dtype=float)
            prob[:n, n] = np.asarray(intel["sink_column"], dtype=float)  # sensor -> sink
        net = cls(positions, sink, link_mode, prob, params, seed)
        net.meta = {"deployment": "intel", "sensor_ids": [s["id"] for s in intel["sensors"]]}
        return net

    # ---- geometry --------------------------------------------------------------
    def xy(self, i):
        return self.sink if i == SINK else self.pos[i]

    def dist(self, a, b):
        pa, pb = self.xy(a), self.xy(b)
        return float(math.hypot(pa[0] - pb[0], pa[1] - pb[1]))

    def alive_indices(self):
        return np.flatnonzero(self.alive)

    def n_alive(self):
        return int(self.alive.sum())

    # ---- the one place energy is charged ---------------------------------------
    def _charge(self, i, cost, kind):
        """Charge `cost` J to sensor i. Return True if it could pay. A node that
        cannot pay uses up what it has, dies, and the operation does not happen."""
        if not self.alive[i]:
            return False
        if cost <= self.energy[i]:
            paid, ok = cost, True
            self.energy[i] -= cost
        else:
            paid, ok = self.energy[i], False
            self.energy[i] = 0.0
        self.round_energy_spent += paid
        self.total_energy_spent += paid
        if kind == "tx":
            self.spent_tx += paid
        elif kind == "rx":
            self.spent_rx += paid
        else:
            self.spent_agg += paid
        if self.energy[i] <= 0.0:
            self.alive[i] = False
            self.death_round[i] = self.current_round
        return ok

    # ---- operations used by protocols ---------------------------------------------
    def generate(self, i):
        """Sensor i produces one reading (one packet) this round."""
        self.round_generated += 1
        self.total_generated += 1

    def aggregate(self, i, n_signals):
        """Cluster head i fuses n_signals signals. False if it could not pay (it dies)."""
        return self._charge(i, aggregation_cost(self.params.packet_bits, n_signals), "agg")

    def send(self, src, dst, payload=1):
        """Send one packet from sensor src to dst (a sensor index or SINK).

        `payload` is how many readings the packet carries; it is added to
        packets_delivered when the packet reaches the sink. Returns True if the
        packet was delivered. Costs follow the conventions in the module docstring.
        """
        if src == dst:
            raise ValueError("a node cannot send to itself")
        if src == SINK or not self.alive[src]:
            return False
        if dst != SINK and not self.alive[dst]:
            return False
        bits = self.params.packet_bits
        tx = radio_cost(bits, self.dist(src, dst))
        rx = rx_cost(bits)
        if self.link_mode == "ideal":
            attempts_allowed, p = 1, 1.0
        else:
            attempts_allowed = self.params.max_attempts
            p = self.prob[src, self.n if dst == SINK else dst]
        self.hops_attempted += 1
        delivered = False
        for _ in range(attempts_allowed):
            if not self._charge(src, tx, "tx"):
                break                         # the sender cannot pay: no attempt made
            self.attempts_total += 1
            if dst != SINK and not self._charge(dst, rx, "rx"):
                break                         # the receiver died: the attempt is lost
            if p >= 1.0 or self.rng_link.random() < p:
                delivered = True
                break
        if delivered:
            self.hops_delivered += 1
            if dst == SINK:
                self.round_delivered += payload
                self.total_delivered += payload
        return delivered

    # ---- round bookkeeping ---------------------------------------------------------
    def begin_round(self, r):
        self.current_round = r
        self.round_energy_spent = 0.0
        self.round_generated = 0
        self.round_delivered = 0

    def lifetime_rounds(self):
        """Rounds in which the first node died, half the nodes were dead, and the
        last node died. None if that has not happened."""
        d = np.sort(self.death_round[self.death_round >= 0])
        fnd = int(d[0]) if len(d) >= 1 else None
        half = math.ceil(self.n / 2)
        hnd = int(d[half - 1]) if len(d) >= half else None
        lnd = int(d[-1]) if len(d) == self.n else None
        return fnd, hnd, lnd


# ---------------------------------------------------------------- run loop
@dataclass
class RunResult:
    rows: list = field(default_factory=list)   # one dict per round
    summary: dict = field(default_factory=dict)


ROW_FIELDS = ["round", "alive", "energy_spent", "packets_generated", "packets_delivered"]


def run_simulation(net, protocol, meta=None):
    """Run `protocol` on `net` round by round.

    A protocol is any object with run_round(net, r). The loop stops when every
    sensor is dead or after params.round_cap rounds, whichever comes first.
    """
    cap = net.params.round_cap
    stop_reason = "round_cap"
    rows = []
    r = 0
    if net.n_alive() == 0:
        stop_reason = "all_dead"
    else:
        for r in range(1, cap + 1):
            net.begin_round(r)
            protocol.run_round(net, r)
            rows.append({
                "round": r,
                "alive": net.n_alive(),
                "energy_spent": net.round_energy_spent,
                "packets_generated": net.round_generated,
                "packets_delivered": net.round_delivered,
            })
            if net.n_alive() == 0:
                stop_reason = "all_dead"
                break
    fnd, hnd, lnd = net.lifetime_rounds()
    spent = net.total_energy_spent
    summary = {
        "protocol": getattr(protocol, "name", type(protocol).__name__),
        "link_mode": net.link_mode,
        "seed": net.seed,
        "n_sensors": net.n,
        "sink": [float(net.sink[0]), float(net.sink[1])],
        "params": asdict(net.params),
        "radio": {"e_elec": E_ELEC, "efs": EFS, "emp": EMP, "d0": D0, "e_da": E_DA},
        "stopped_round": r,
        "stop_reason": stop_reason,
        "fnd": fnd,
        "hnd": hnd,
        "lnd": lnd,
        "packets_generated": net.total_generated,
        "packets_delivered": net.total_delivered,
        "pdr": net.total_delivered / net.total_generated if net.total_generated else None,
        "energy_spent": spent,
        "packets_per_joule": net.total_delivered / spent if spent > 0 else None,
        "energy_tx": net.spent_tx,
        "energy_rx": net.spent_rx,
        "energy_agg": net.spent_agg,
        "hop_attempts": net.attempts_total,
        "hops_attempted": net.hops_attempted,
        "hops_delivered": net.hops_delivered,
    }
    if meta:
        summary.update(meta)
    return RunResult(rows=rows, summary=summary)


def save_run(result, out_dir, run_id):
    """Save a run as <run_id>.csv (one row per round) and <run_id>.json (config and summary)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{run_id}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROW_FIELDS)
        w.writeheader()
        w.writerows(result.rows)
    with open(out_dir / f"{run_id}.json", "w") as f:
        json.dump(result.summary, f, indent=1)
