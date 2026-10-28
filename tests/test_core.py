"""Tests for the link layer, the round loop, the stop rules and the loaders."""

import csv
import json
import math
from pathlib import Path

import numpy as np

from sim import core
from sim.core import (Network, Params, ROW_FIELDS, SINK, radio_cost, run_simulation,
                      rx_cost, save_run)

ROOT = Path(__file__).resolve().parents[1]
BITS = core.PACKET_BITS


class DirectToSink:
    """Test stand-in: every alive sensor sends its own reading straight to the sink."""
    name = "direct_to_sink"

    def run_round(self, net, r):
        for i in net.alive_indices():
            net.generate(i)
            net.send(i, SINK)


class Idle:
    """Test stand-in that does nothing, so no energy is ever spent."""
    name = "idle"

    def run_round(self, net, r):
        pass


def line_net(link_mode="ideal", p=1.0, e_init=0.5, n=3, cap=20000, seed=1):
    """n sensors on a line, 10 m apart, sink 10 m past the last one."""
    pos = [[10.0 * k, 0.0] for k in range(n)]
    sink = [10.0 * n, 0.0]
    prob = np.full((n + 1, n + 1), p)
    return Network(pos, sink, link_mode, prob if link_mode == "measured" else None,
                   Params(e_init=e_init, round_cap=cap), seed=seed)


# ---------------------------------------------------------------- link layer
def test_ideal_mode_is_one_attempt_charged_to_both_ends():
    net = line_net("ideal")
    assert net.send(0, 1) is True
    assert net.attempts_total == 1
    assert math.isclose(0.5 - net.energy[0], radio_cost(BITS, 10.0), rel_tol=1e-12)
    assert math.isclose(0.5 - net.energy[1], rx_cost(BITS), rel_tol=1e-12)
    assert net.energy[2] == 0.5


def test_sending_to_the_sink_charges_only_the_sender():
    net = line_net("ideal")
    assert net.send(2, SINK) is True
    assert math.isclose(0.5 - net.energy[2], radio_cost(BITS, 10.0), rel_tol=1e-12)
    assert net.energy[0] == 0.5 and net.energy[1] == 0.5


def test_measured_mode_with_probability_zero_makes_exactly_eight_attempts():
    net = line_net("measured", p=0.0)
    assert net.send(0, 1) is False
    assert net.attempts_total == 8
    assert math.isclose(0.5 - net.energy[0], 8 * radio_cost(BITS, 10.0), rel_tol=1e-12)
    assert math.isclose(0.5 - net.energy[1], 8 * rx_cost(BITS), rel_tol=1e-12)


def test_measured_mode_with_probability_one_makes_one_attempt():
    net = line_net("measured", p=1.0)
    assert net.send(0, 1) is True
    assert net.attempts_total == 1


def test_a_hop_never_makes_more_than_eight_attempts():
    net = line_net("measured", p=0.1, e_init=1e9)
    for _ in range(500):
        before = net.attempts_total
        net.send(0, 1)
        assert net.attempts_total - before <= 8


def test_a_packet_that_reaches_the_sink_adds_its_payload_to_packets_delivered():
    net = line_net("ideal")
    net.begin_round(1)
    net.send(0, 1)                       # not the sink: nothing delivered yet
    assert net.round_delivered == 0
    net.send(2, SINK, payload=5)
    assert net.round_delivered == 5 and net.total_delivered == 5


def test_a_dead_node_cannot_send_or_receive():
    net = line_net("ideal")
    net.alive[1] = False
    before = net.energy.copy()
    assert net.send(1, 0) is False       # dead sender
    assert net.send(0, 1) is False       # dead receiver
    assert np.array_equal(net.energy, before)


def test_a_node_that_cannot_pay_dies_and_energy_never_goes_below_zero():
    net = line_net("ideal", e_init=1e-5)  # less than one packet costs
    net.begin_round(4)
    assert net.send(0, 1) is False
    assert net.energy[0] == 0.0 and not net.alive[0]
    assert net.death_round[0] == 4
    assert net.energy.min() >= 0.0


def test_a_receiver_that_cannot_pay_dies_and_the_attempt_is_lost():
    net = line_net("ideal")
    net.energy[1] = 1e-5
    assert net.send(0, 1) is False
    assert not net.alive[1] and net.energy[1] == 0.0
    assert net.alive[0]


def test_aggregation_is_charged_to_the_cluster_head():
    net = line_net("ideal")
    assert net.aggregate(1, 4) is True
    assert math.isclose(0.5 - net.energy[1], core.aggregation_cost(BITS, 4), rel_tol=1e-12)
    assert net.spent_agg > 0


def test_a_node_cannot_send_to_itself():
    net = line_net("ideal")
    try:
        net.send(1, 1)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# ---------------------------------------------------------------- round loop
def test_a_run_stops_when_every_sensor_is_dead():
    net = line_net("ideal", e_init=2e-3)
    result = run_simulation(net, DirectToSink())
    assert result.summary["stop_reason"] == "all_dead"
    assert result.rows[-1]["alive"] == 0
    assert result.summary["stopped_round"] == len(result.rows) < core.ROUND_CAP
    assert not net.alive.any()


def test_a_run_stops_at_the_round_cap_when_sensors_are_still_alive():
    net = line_net("ideal", cap=7)
    result = run_simulation(net, Idle())
    assert result.summary["stop_reason"] == "round_cap"
    assert result.summary["stopped_round"] == 7 == len(result.rows)
    assert result.rows[-1]["alive"] == 3


def test_the_round_cap_is_20000_by_default():
    assert core.ROUND_CAP == 20000 and Params().round_cap == 20000


def test_the_round_cap_is_the_stopping_rule_even_when_energy_is_plentiful():
    net = line_net("ideal", e_init=1e9, cap=25)
    result = run_simulation(net, DirectToSink())
    assert result.summary["stopped_round"] == 25
    assert result.summary["stop_reason"] == "round_cap"


def test_the_log_has_one_row_per_round_with_the_required_columns():
    net = line_net("ideal", e_init=2e-3)
    result = run_simulation(net, DirectToSink())
    assert set(result.rows[0]) == set(ROW_FIELDS)
    assert [row["round"] for row in result.rows] == list(range(1, len(result.rows) + 1))
    first = result.rows[0]
    assert first["alive"] == 3 and first["packets_generated"] == 3 and first["packets_delivered"] == 3


def test_energy_spent_in_the_log_equals_the_energy_that_left_the_batteries():
    net = line_net("measured", p=0.3, e_init=0.01, n=4)
    result = run_simulation(net, DirectToSink())
    logged = sum(row["energy_spent"] for row in result.rows)
    removed = 4 * 0.01 - float(net.energy.sum())
    assert math.isclose(logged, removed, rel_tol=1e-9)
    assert math.isclose(result.summary["energy_spent"], logged, rel_tol=1e-9)


def test_first_half_and_last_node_dead_rounds_are_recorded_in_order():
    net = line_net("ideal", e_init=3e-3, n=4)
    result = run_simulation(net, DirectToSink())
    s = result.summary
    assert s["fnd"] is not None and s["hnd"] is not None and s["lnd"] is not None
    assert s["fnd"] <= s["hnd"] <= s["lnd"] == s["stopped_round"]


def test_lifetime_rounds_are_none_when_nobody_has_died():
    net = line_net("ideal", e_init=1e9, cap=5)
    result = run_simulation(net, DirectToSink())
    assert (result.summary["fnd"], result.summary["hnd"], result.summary["lnd"]) == (None, None, None)


# ---------------------------------------------------------------- randomness
def test_same_seed_gives_the_same_run_and_a_different_seed_a_different_one():
    a = run_simulation(line_net("measured", p=0.4, e_init=0.01, seed=11), DirectToSink())
    b = run_simulation(line_net("measured", p=0.4, e_init=0.01, seed=11), DirectToSink())
    c = run_simulation(line_net("measured", p=0.4, e_init=0.01, seed=12), DirectToSink())
    assert a.rows == b.rows
    assert a.rows != c.rows


def test_protocol_random_choices_do_not_change_the_link_outcomes():
    a = line_net("measured", p=0.5, e_init=1e9, seed=5)
    b = line_net("measured", p=0.5, e_init=1e9, seed=5)
    b.rng_protocol.random(1000)          # a protocol that draws many random numbers
    out_a = [a.send(0, 1) for _ in range(200)]
    out_b = [b.send(0, 1) for _ in range(200)]
    assert out_a == out_b and a.attempts_total == b.attempts_total


def test_runs_are_saved_as_one_csv_and_one_json(tmp_path):
    net = line_net("ideal", e_init=2e-3)
    result = run_simulation(net, DirectToSink(), meta={"level": "toy", "param_set": "none"})
    save_run(result, tmp_path, "toy-run")
    with open(tmp_path / "toy-run.csv") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == ROW_FIELDS and len(rows) == len(result.rows)
    config = json.load(open(tmp_path / "toy-run.json"))
    assert config["protocol"] == "direct_to_sink" and config["level"] == "toy"
    assert config["params"]["round_cap"] == 20000 and config["params"]["max_attempts"] == 8
    assert config["radio"]["e_elec"] == 50e-9 and config["stop_reason"] == "all_dead"


# ---------------------------------------------------------------- deployments
def test_the_intel_network_has_52_sensors_the_sink_and_the_right_probabilities():
    net = Network.from_intel_file(ROOT / "data" / "intel.json", "measured")
    intel = json.load(open(ROOT / "data" / "intel.json"))
    assert net.n == 52 and net.prob.shape == (53, 53)
    assert list(net.sink) == [19.5, 19.0]
    ids = [s["id"] for s in intel["sensors"]]
    assert 3 not in ids and 5 not in ids and 0 not in ids
    pm = intel["prob_matrix"]
    a, b = ids.index(1), ids.index(2)
    assert net.prob[a, b] == pm[a][b] and net.prob[b, a] == pm[b][a]
    assert net.prob[ids.index(15), net.n] == 0.0           # mote 15 never reaches the sink
    assert net.prob[ids.index(1), net.n] == intel["sink_column"][ids.index(1)] > 0
    assert (net.prob[net.n, :] == 0).all()                   # the sink never sends


def test_no_distance_in_the_intel_lab_reaches_the_crossover():
    net = Network.from_intel_file(ROOT / "data" / "intel.json", "ideal")
    longest = max(net.dist(i, j) for i in range(net.n) for j in range(net.n) if i != j)
    to_sink = max(net.dist(i, SINK) for i in range(net.n))
    assert longest < core.D0 and to_sink < core.D0
    assert 47.0 < longest < 47.5                              # 47.2 m, as in the data section


def test_a_random_layout_loads_with_the_intel_box_and_sink():
    net = Network.from_layout_file(ROOT / "data" / "layouts" / "random52_seed001.json")
    assert net.n == 52 and list(net.sink) == [19.5, 19.0] and net.link_mode == "ideal"
    assert net.pos[:, 0].min() >= 0.5 and net.pos[:, 0].max() <= 40.5
    assert net.pos[:, 1].min() >= 1.0 and net.pos[:, 1].max() <= 31.0
