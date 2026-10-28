"""Hand-checked tests of the five protocols on 10-node toy layouts.

Every expected cluster head, chain and sleeping node below was worked out by hand from the
coordinates in the comments, before the code was run. A protocol is not allowed into the
main comparison until these pass (the second check is the 100-node reproduction).

Toy layout A (LEACH, R-LEACH, HEED, PEGASIS): two rows of five sensors,

    y = 4:   5(0,4)  6(3,4)  7(6,4)  8(9,4)  9(12,4)
    y = 0:   0(0,0)  1(3,0)  2(6,0)  3(9,0)  4(12,0)        sink at (6, 40)

Toy layout B (ECH): sensors 0..5 on a hexagon of radius 0.5 around (10, 10), sensor 6 in
its centre, and three lonely sensors 7 (30,10), 8 (10,30), 9 (30,30); sink at (20, 25).
"""

import math
import re
from pathlib import Path

import numpy as np
import pytest

from sim import core
from sim.core import Network, Params, SINK, run_simulation
from sim.protocols import MODULES, common, ech, heed, leach, make, pegasis, rleach
from sim.protocols.common import State

ROW_A = [(3.0 * k, 0.0) for k in range(5)] + [(3.0 * k, 4.0) for k in range(5)]
SINK_A = (6.0, 40.0)
HEX = [(10.0 + 0.5 * math.cos(math.radians(60 * k)), 10.0 + 0.5 * math.sin(math.radians(60 * k)))
       for k in range(6)]
LAYOUT_B = HEX + [(10.0, 10.0), (30.0, 10.0), (10.0, 30.0), (30.0, 30.0)]
SINK_B = (20.0, 25.0)


class FakeRng:
    """Hands out prepared arrays of 'random' numbers, in the order they are asked for."""

    def __init__(self, *arrays):
        self.queue = [np.asarray(a, dtype=float) for a in arrays]
        self.calls = 0

    def random(self, n):
        a = self.queue.pop(0)
        assert len(a) == n, "protocol asked for %d numbers, test prepared %d" % (n, len(a))
        self.calls += 1
        return a


def draws(default, **special):
    """Array of 10 numbers equal to `default` except for the sensors named n<i>=value."""
    a = np.full(10, float(default))
    for key, value in special.items():
        a[int(key[1:])] = value
    return a


def make_state(module, positions, sink, config=None, energy=None, e_init=0.5):
    net = Network(positions, sink, "ideal", None, Params(e_init=e_init))
    if energy is not None:
        net.energy[:] = energy
    state = State(net, {**module.DEFAULTS, **(config or {})})
    return net, state


def step(module, state, rng, r):
    state.round = r
    plan = module.setup_round(state, rng)
    return plan, module.route(state)


# ---------------------------------------------------------------- the interface
def test_every_protocol_file_has_setup_round_and_route():
    assert set(MODULES) == {"leach", "heed", "pegasis", "rleach", "ech"}
    for name, module in MODULES.items():
        assert callable(module.setup_round) and callable(module.route), name
        assert module.NAME == name


def test_a_protocol_sees_positions_and_energies_but_never_the_delivery_probabilities():
    prob = np.full((11, 11), 0.3)
    net = Network(ROW_A, SINK_A, "measured", prob, Params())
    state = State(net, {})
    assert not hasattr(state, "prob") and not hasattr(state, "net")
    assert not any(isinstance(v, Network) for v in vars(state).values())
    assert not state.energy.flags.writeable and not state.alive.flags.writeable
    with pytest.raises(ValueError):
        state.energy[0] = 1.0


def test_no_protocol_file_refers_to_the_links_or_the_network_object():
    # the delivery probabilities live in Network.prob and are used only by Network.send in sim/core.py;
    # the code of the protocol files (docstrings and comments left out) never names them
    banned = re.compile(r"\.prob\b|prob_matrix|sink_column|rng_link|link_mode|Network|intel\.json|measured")
    folder = Path(__file__).resolve().parents[1] / "sim" / "protocols"
    for path in sorted(folder.glob("*.py")):
        text = re.sub(r'"""[\s\S]*?"""', "", path.read_text(encoding="utf-8"))
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        found = banned.search(code)
        assert not found, (path.name, found.group(0))


def test_the_only_random_source_is_the_one_seeded_generator_handed_to_each_protocol():
    # protocols and the pilot script never create or call a random source of their own: the protocols
    # draw from the `rng` they are given, which is Network.rng_protocol, built from SeedSequence(seed)
    banned = re.compile(r"import random|from random|np\.random|numpy\.random|default_rng|RandomState|SeedSequence|time\.time|os\.urandom")
    root = Path(__file__).resolve().parents[1]
    for path in sorted((root / "sim" / "protocols").glob("*.py")) + [root / "scripts" / "pilot.py"]:
        text = re.sub(r'"""[\s\S]*?"""', "", path.read_text(encoding="utf-8"))
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        found = banned.search(code)
        assert not found, (path.name, found.group(0))
    core_source = (root / "sim" / "core.py").read_text(encoding="utf-8")
    assert core_source.count("SeedSequence(seed)") == 1 and core_source.count("default_rng(") == 2


def test_the_same_seed_gives_the_same_pilot_style_run_for_every_protocol():
    for name in ("leach", "heed", "pegasis", "rleach", "ech"):
        traces = []
        for _ in range(2):
            net = Network(ROW_A, SINK_A, "measured", np.full((11, 11), 0.5), Params(e_init=0.01), seed=1)
            traces.append(run_simulation(net, make(name)).rows)
        assert traces[0] == traces[1], name


@pytest.mark.parametrize("name", ["leach", "heed", "pegasis", "rleach", "ech"])
def test_the_first_round_plan_does_not_depend_on_the_delivery_probabilities(name):
    plans = []
    for p in (0.1, 0.9):
        net = Network(ROW_A, SINK_A, "measured", np.full((11, 11), p), Params(), seed=7)
        runner = make(name)
        runner.state = State(net, runner.config)
        runner.state.round = 1
        plans.append(runner.module.setup_round(runner.state, net.rng_protocol))
    assert plans[0] == plans[1]


# ---------------------------------------------------------------- LEACH
def test_leach_threshold_values():
    # p = 0.2: an epoch is 5 rounds, T = 0.2, 0.25, 0.3333, 0.5, 1
    assert common.leach_epoch(0.2) == 5
    assert [round(common.leach_threshold(0.2, k), 6) for k in range(5)] == [0.2, 0.25, 0.333333, 0.5, 1.0]
    assert common.leach_epoch(0.05) == 20 and common.leach_epoch(0.08) == 12
    assert common.leach_epoch(0.03) == 33 and common.leach_epoch(0.12) == 8


def test_leach_round_one_picks_the_two_sensors_below_the_threshold_and_members_join_the_nearest():
    net, state = make_state(leach, ROW_A, SINK_A, {"p": 0.2})
    plan, hops = step(leach, state, FakeRng(draws(0.9, n4=0.1, n9=0.19)), 1)   # T = 0.2: sensors 4 and 9
    assert plan["heads"] == [4, 9]
    # by hand: 0,1,2,3 are nearer to 4 (12,0) than to 9 (12,4); 5,6,7,8 are nearer to 9
    assert plan["assign"] == {0: 4, 1: 4, 2: 4, 3: 4, 5: 9, 6: 9, 7: 9, 8: 9}
    assert hops == [(0, 4), (1, 4), (2, 4), (3, 4), (5, 9), (6, 9), (7, 9), (8, 9), (4, SINK), (9, SINK)]
    assert plan["sensing"] == list(range(10))


def test_leach_a_head_cannot_serve_again_until_the_epoch_is_over():
    net, state = make_state(leach, ROW_A, SINK_A, {"p": 0.2})
    step(leach, state, FakeRng(draws(0.9, n4=0.1, n9=0.19)), 1)
    plan, _ = step(leach, state, FakeRng(draws(0.0)), 2)         # T = 0.25, every draw passes
    assert plan["heads"] == [0, 1, 2, 3, 5, 6, 7, 8]            # not 4 and 9
    assert plan["assign"][4] == 3 and plan["assign"][9] == 8     # their nearest heads: (9,0) and (9,4)


def test_leach_last_round_of_the_epoch_has_threshold_one_and_a_new_epoch_resets_the_set():
    net, state = make_state(leach, ROW_A, SINK_A, {"p": 0.2})
    step(leach, state, FakeRng(draws(0.9, n4=0.1, n9=0.19)), 1)
    for r in (2, 3, 4):
        plan, _ = step(leach, state, FakeRng(draws(0.99)), r)    # T = .25, .33, .5: nobody
        assert plan["heads"] == []
    plan, _ = step(leach, state, FakeRng(draws(0.99)), 5)        # T = 1: everyone still eligible
    assert plan["heads"] == [0, 1, 2, 3, 5, 6, 7, 8]
    plan, _ = step(leach, state, FakeRng(draws(0.1)), 6)         # round 6 starts epoch 2: T = 0.2
    assert plan["heads"] == list(range(10))


def test_leach_with_no_head_sends_everything_straight_to_the_sink_and_counts_the_round():
    net, state = make_state(leach, ROW_A, SINK_A, {"p": 0.2})
    plan, hops = step(leach, state, FakeRng(draws(0.9)), 1)
    assert plan["heads"] == [] and all(dst == SINK for _, dst in hops) and len(hops) == 10
    assert state.stats["rounds_without_head"] == 1


def test_leach_never_picks_a_dead_sensor():
    net, state = make_state(leach, ROW_A, SINK_A, {"p": 0.2})
    net.alive[4] = False
    plan, _ = step(leach, state, FakeRng(draws(0.0)), 1)
    assert 4 not in plan["heads"] and 4 not in plan["sensing"] and 4 not in plan["assign"]


def test_leach_round_one_energy_ledger_matches_a_hand_calculation():
    net = Network(ROW_A, SINK_A, "ideal", None, Params(round_cap=1))
    net.rng_protocol = FakeRng(draws(0.9, n4=0.1, n9=0.19))
    result = run_simulation(net, make("leach", {"p": 0.2}))
    bits = core.PACKET_BITS
    members = {0: 4, 1: 4, 2: 4, 3: 4, 5: 9, 6: 9, 7: 9, 8: 9}
    tx = sum(core.radio_cost(bits, math.dist(ROW_A[m], ROW_A[h])) for m, h in members.items())
    rx = 8 * core.rx_cost(bits)
    agg = 2 * core.aggregation_cost(bits, 5)                       # each head fuses 4 members + itself
    to_sink = sum(core.radio_cost(bits, math.dist(ROW_A[h], SINK_A)) for h in (4, 9))
    assert math.isclose(result.rows[0]["energy_spent"], tx + rx + agg + to_sink, rel_tol=1e-12)
    assert result.rows[0]["packets_generated"] == 10 and result.rows[0]["packets_delivered"] == 10


# ---------------------------------------------------------------- R-LEACH
def test_rleach_round_one_is_plain_leach_whatever_the_energy():
    energy = np.full(10, 0.5)
    energy[9] = 0.05
    net, state = make_state(rleach, ROW_A, SINK_A, {"p": 0.2, "k_opt": 2.0}, energy=energy)
    plan, _ = step(rleach, state, FakeRng(draws(0.9, n4=0.1, n9=0.19)), 1)   # Eq. 4, no energy factor
    assert plan["heads"] == [4, 9]


def test_rleach_round_two_scales_the_threshold_by_residual_energy_and_k_opt():
    net, state = make_state(rleach, ROW_A, SINK_A, {"p": 0.2, "k_opt": 2.0})
    step(rleach, state, FakeRng(draws(0.9, n4=0.1, n9=0.19)), 1)
    net.energy[3] = 0.25                                           # half of the initial energy
    # round 2: LEACH T = 0.25, so T(n) = 0.25 * 1 * 2 = 0.5, and 0.25 * 0.5 * 2 = 0.25 for sensor 3
    plan, _ = step(rleach, state, FakeRng(draws(0.9, n2=0.4, n3=0.4, n4=0.01, n9=0.01)), 2)
    assert plan["heads"] == [2]        # 2: 0.4 < 0.5; 3: 0.4 > 0.25; 4 and 9 were heads already


def test_rleach_threshold_is_capped_at_one():
    net, state = make_state(rleach, ROW_A, SINK_A, {"p": 0.2, "k_opt": 100.0})
    step(rleach, state, FakeRng(draws(0.9, n4=0.1, n9=0.19)), 1)
    plan, _ = step(rleach, state, FakeRng(draws(0.999)), 2)      # 0.25 * 100 would be 25, kept at 1
    assert plan["heads"] == [0, 1, 2, 3, 5, 6, 7, 8]


def test_rleach_k_opt_free_space_form_on_a_diamond():
    # four sensors 10 m from a central sink in a 20 m x 20 m box: sqrt(4 / 2 pi) * 20 / 10
    pos = [(10.0, 0.0), (-10.0, 0.0), (0.0, 10.0), (0.0, -10.0)]
    net, state = make_state(rleach, pos, (0.0, 0.0))
    assert math.isclose(rleach.optimal_clusters(state), math.sqrt(4 / (2 * math.pi)) * 2.0, rel_tol=1e-12)


def test_rleach_k_opt_uses_the_multipath_form_beyond_the_crossover():
    pos = [(100.0, 0.0), (-100.0, 0.0), (0.0, 100.0), (0.0, -100.0)]
    net, state = make_state(rleach, pos, (0.0, 0.0))
    expected = math.sqrt(4 / (2 * math.pi)) * math.sqrt(core.EFS / core.EMP) * 200.0 / 100.0 ** 2
    assert math.isclose(rleach.optimal_clusters(state), max(expected, 1.0), rel_tol=1e-12)


# ---------------------------------------------------------------- HEED
def test_heed_toy_layout_heads_and_members_by_hand():
    # cluster range 4.5 m: neighbours are the left/right ones (3 m) and the one across (4 m).
    # CH_prob starts at 0.25, then 0.5, then 1.
    #  iteration 1 (0.25): sensor 4 draws 0.1 and becomes a tentative head
    #  iteration 2 (0.5):  sensors 3 and 9 have heard 4 and stay quiet; sensor 5 draws 0.3 and becomes tentative
    #  iteration 3 (1.0):  4 and 5 are their own best and become final; 3, 9 (hear 4) and 0, 6 (hear 5) are covered;
    #                      1, 2, 7 and 8 hear nobody and become final heads
    net, state = make_state(heed, ROW_A, SINK_A, {"c_prob": 0.25, "cluster_radius": 4.5})
    rng = FakeRng(draws(0.9, n4=0.1), draws(0.9, n5=0.3), draws(0.9))
    plan, hops = step(heed, state, rng, 1)
    assert rng.calls == 3
    assert plan["heads"] == [1, 2, 4, 5, 7, 8]
    # cost = mean distance to the neighbours in range: 1, 2, 7, 8 have 3.333, 4 and 5 have 3.5.
    # 0 hears 1 (3.333, 3 m) and 5 (3.5): joins 1.   3 hears 2 (3.333, 3 m), 8 (3.333, 4 m), 4 (3.5): joins 2.
    # 6 hears 7 (3.333, 3 m), 1 (3.333, 4 m), 5 (3.5): joins 7.   9 hears 8 (3.333) and 4 (3.5): joins 8.
    assert plan["assign"] == {0: 1, 3: 2, 6: 7, 9: 8}
    assert hops[:4] == [(0, 1), (3, 2), (6, 7), (9, 8)] and hops[4:] == [(h, SINK) for h in plan["heads"]]


def test_heed_low_energy_sensors_start_at_p_min_and_need_twelve_iterations():
    # p_min = 0.0005 doubles 11 times before it reaches 1, so phase II lasts 12 iterations
    # (Lemma 1: N_iter <= ceil(log2(1 / p_min)) + 1 = 12). Nobody draws below the probability,
    # so everybody is uncovered at the end and becomes a final head.
    net, state = make_state(heed, ROW_A, SINK_A, {"cluster_radius": 4.5}, energy=np.full(10, 1e-6))
    rng = FakeRng(*[draws(0.9) for _ in range(12)])
    plan, _ = step(heed, state, rng, 1)
    assert rng.calls == 12 and state.stats["heed_iterations_max"] == 12
    assert plan["heads"] == list(range(10)) and plan["assign"] == {}


def test_heed_a_sensor_alone_in_its_range_is_its_own_head():
    net, state = make_state(heed, [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)], (0.0, 100.0), {"cluster_radius": 25.0})
    plan, _ = step(heed, state, FakeRng(*[np.full(3, 0.9) for _ in range(6)]), 1)
    assert plan["heads"] == [0, 1, 2]


# ---------------------------------------------------------------- PEGASIS
def test_pegasis_chain_is_the_greedy_snake_from_the_farthest_sensor():
    # farthest from (6, 40): sensors 0 and 4 tie at 40.45, the lower index 0 starts.
    # 0 -> 1 (3 m, not 5 at 4 m) -> 2 -> 3 -> 4 -> 9 (4 m up) -> 8 -> 7 -> 6 -> 5
    net, state = make_state(pegasis, ROW_A, SINK_A)
    plan, hops = step(pegasis, state, None, 3)
    assert plan["chain"] == [0, 1, 2, 3, 4, 9, 8, 7, 6, 5]
    assert plan["leader"] == 2                                  # round 3: sensor number 3 mod 10 - 1, i.e. index 2
    assert hops == [(0, 1), (1, 2),
                    (5, 6), (6, 7), (7, 8), (8, 9), (9, 4), (4, 3), (3, 2),
                    (2, SINK)]


def test_pegasis_leader_rotates_through_the_sensors_in_turn():
    net, state = make_state(pegasis, ROW_A, SINK_A)
    leaders = [step(pegasis, state, None, r)[0]["leader"] for r in range(1, 13)]
    assert leaders == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1]
    assert state.stats["chain_builds"] == 1                     # the chain is built once while nobody dies


def test_pegasis_rebuilds_the_chain_without_a_dead_sensor_and_the_greedy_leaves_sensor_9_to_the_end():
    net, state = make_state(pegasis, ROW_A, SINK_A)
    step(pegasis, state, None, 1)
    net.alive[4] = False
    # 0 -> 1 -> 2 -> 3 -> 8 (4 m) -> 7 (ties with 9 at 3 m, lower index) -> 6 -> 5 -> 9 (12 m jump back)
    plan, hops = step(pegasis, state, None, 5)
    assert plan["chain"] == [0, 1, 2, 3, 8, 7, 6, 5, 9]
    assert state.stats["chain_builds"] == 2
    assert plan["leader"] == 5                                  # alive sorted [0,1,2,3,5,...]: round 5 -> fifth, sensor 5
    assert hops == [(0, 1), (1, 2), (2, 3), (3, 8), (8, 7), (7, 6), (6, 5),
                    (9, 5),
                    (5, SINK)]


def test_pegasis_one_round_energy_ledger_matches_a_hand_calculation():
    net = Network(ROW_A, SINK_A, "ideal", None, Params(round_cap=1))
    result = run_simulation(net, make("pegasis"))               # round 1: leader is sensor 0, the chain end
    chain = [0, 1, 2, 3, 4, 9, 8, 7, 6, 5]
    bits = core.PACKET_BITS
    tx = sum(core.radio_cost(bits, math.dist(ROW_A[a], ROW_A[b])) for a, b in zip(chain[1:], chain[:-1]))
    tx += core.radio_cost(bits, math.dist(ROW_A[0], SINK_A))
    rx = 9 * core.rx_cost(bits)
    agg = 9 * core.aggregation_cost(bits, 2)                    # every sensor but the far end fuses own + received
    assert math.isclose(result.rows[0]["energy_spent"], tx + rx + agg, rel_tol=1e-12)
    assert result.rows[0]["packets_delivered"] == 10


# ---------------------------------------------------------------- ECH
def test_ech_sensing_disk_test():
    r = 1.0
    ring = np.array(HEX)
    centre = np.array([10.0, 10.0])
    assert ech.fully_monitored(centre, ring, r)                                      # the hexagon covers its centre disk
    assert not ech.fully_monitored(centre, ring[:2], r)                              # two vertices leave gaps
    assert ech.fully_monitored(centre, np.array([[10.0, 10.0]]), r)                  # a twin at the same spot covers it
    assert not ech.fully_monitored(centre, np.array([[10.5, 10.0]]), r)              # an offset neighbour does not
    assert not ech.fully_monitored(centre, np.empty((0, 2)), r)


def test_ech_the_centre_sensor_sleeps_when_the_hexagon_around_it_is_awake():
    # equal energy: ties go to the lower index, so 0..5 decide first and stay awake (a vertex's disk
    # sticks out 1 m beyond the ring and cannot be covered); 6 decides last, its disk is covered, it sleeps.
    # 7, 8 and 9 are more than 2 m from everyone: unpaired, always awake.
    net, state = make_state(ech, LAYOUT_B, SINK_B, {"overlap_radius": 1.0})
    awake, unpaired = ech.choose_awake(state, state.alive_indices(), 1.0)
    assert list(np.flatnonzero(~awake)) == [6]
    assert unpaired == 3


def test_ech_the_sensor_with_most_energy_decides_first_and_stays_awake():
    energy = np.full(10, 0.4)
    energy[6] = 0.5
    net, state = make_state(ech, LAYOUT_B, SINK_B, {"overlap_radius": 1.0}, energy=energy)
    awake, _ = ech.choose_awake(state, state.alive_indices(), 1.0)
    assert awake.all()                  # 6 decides first with nobody awake, then no vertex can be covered


def test_ech_heads_members_and_the_direct_to_sink_rule():
    # awake: 0..5, 7, 8, 9 -> n_active = 9, k_opt = sqrt(9 / 2.4033) = 1.935, p_opt = 0.215, K = 2
    # sensors 0 (draw 0.1) and 7 (draw 0.2) pass T = 0.215: two candidates, nothing to fix
    # hexagon vertices: 0.5-1 m from head 0, 18 m from the sink: they join 0
    # 8 and 9: 11.2 m from the sink, 20 m or more from any head: they send straight to the sink
    net, state = make_state(ech, LAYOUT_B, SINK_B, {"overlap_radius": 1.0})
    plan, hops = step(ech, state, FakeRng(draws(0.9, n0=0.1, n7=0.2), draws(0.9)), 1)
    assert plan["sensing"] == [0, 1, 2, 3, 4, 5, 7, 8, 9]          # 6 sleeps and senses nothing
    assert plan["heads"] == [0, 7]
    assert plan["assign"] == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 8: SINK, 9: SINK}
    assert state.stats["asleep_node_rounds"] == 1 and state.stats["unpaired_node_rounds"] == 3
    assert hops[-2:] == [(0, SINK), (7, SINK)]


def test_ech_too_many_candidates_the_lowest_chance_go_back_to_normal():
    # candidates 0, 1, 7, 9; K = 2. Local distance = sum of distances to the other candidates:
    # 0: 47.9, 1: 48.1, 7: 59.3, 9: 75.7. Equal energy, so chance = 0.5 + 0.5 * (1 - Ld / Ld_max):
    # 9 has the lowest chance and goes back; among 0, 1, 7 it is 7. Heads: 0 and 1.
    net, state = make_state(ech, LAYOUT_B, SINK_B, {"overlap_radius": 1.0})
    plan, _ = step(ech, state, FakeRng(draws(0.9, n0=0.1, n1=0.1, n7=0.1, n9=0.1), draws(0.9)), 1)
    assert plan["heads"] == [0, 1]
    assert state.stats["head_removals"] == 2
    assert plan["assign"][7] == SINK and plan["assign"][9] == SINK   # nearer to the sink than to head 0


def test_ech_too_few_candidates_far_sensors_get_a_second_draw():
    # only sensor 0 passes the first draw (K = 2). Sensors 7, 8, 9 are farther from 0 than from the
    # sink, so they draw again; sensor 9 draws 0.05 < 0.215 and becomes the second head.
    # The hexagon vertices are about 1 m from 0 and 18 m from the sink: they do not draw again.
    net, state = make_state(ech, LAYOUT_B, SINK_B, {"overlap_radius": 1.0})
    plan, _ = step(ech, state, FakeRng(draws(0.9, n0=0.1), draws(0.9, n9=0.05)), 1)
    assert plan["heads"] == [0, 9]
    assert state.stats["reelections"] == 1


def test_ech_a_recent_head_cannot_be_a_candidate_again():
    net, state = make_state(ech, LAYOUT_B, SINK_B, {"overlap_radius": 1.0})
    step(ech, state, FakeRng(draws(0.9, n0=0.1, n7=0.2), draws(0.9)), 1)
    plan, _ = step(ech, state, FakeRng(draws(0.0), draws(0.0)), 2)   # epoch is 5 rounds: 0 and 7 must rest
    assert 0 not in plan["heads"] and 7 not in plan["heads"]
    assert len(plan["heads"]) == 2


# ---------------------------------------------------------------- the protocols together
@pytest.mark.parametrize("name", ["leach", "heed", "pegasis", "rleach", "ech"])
def test_on_the_toy_layout_alive_never_rises_and_no_energy_goes_negative(name):
    prob = np.full((11, 11), 0.6)
    net = Network(ROW_A, SINK_A, "measured", prob, Params(e_init=0.01), seed=3)
    runner = make(name)
    result = run_simulation(net, runner)
    alive = [row["alive"] for row in result.rows]
    assert alive == sorted(alive, reverse=True)
    assert alive[-1] == 0 and result.summary["stop_reason"] == "all_dead"
    assert runner.min_energy >= 0.0 and net.energy.min() >= 0.0


@pytest.mark.parametrize("name", ["leach", "heed", "pegasis", "rleach", "ech"])
def test_every_hop_comes_after_the_hops_that_feed_it(name):
    net = Network(ROW_A, SINK_A, "ideal", None, Params(e_init=0.01), seed=5)
    runner = make(name)
    runner.state = State(net, runner.config)
    for r in range(1, 40):
        runner.state.round = r
        runner.module.setup_round(runner.state, net.rng_protocol)
        hops = runner.module.route(runner.state)
        for k, (src, dst) in enumerate(hops):
            assert src != dst
            assert all(h[1] != src for h in hops[k + 1:]), (name, r, hops)
        net.energy[:] = net.energy * 0.99
