"""Tests for the shared energy function and the measured-link attempt count.

These run before any protocol exists, so that all five protocols later share one
checked energy function.
"""

import math

import numpy as np

from sim import core
from sim.core import Network, Params, SINK, aggregation_cost, radio_cost, rx_cost


def test_one_4000_bit_packet_over_20_m_costs_the_first_order_amount():
    # exactly 4000 x (50e-9 + 10e-12 x 400) J = 0.000216 J
    assert radio_cost(4000, 20) == 4000 * (50e-9 + 10e-12 * 400)
    assert math.isclose(radio_cost(4000, 20), 0.000216, rel_tol=1e-12)


def test_receiving_a_4000_bit_packet_costs_only_the_electronics():
    assert rx_cost(4000) == 4000 * 50e-9
    assert math.isclose(rx_cost(4000), 0.0002, rel_tol=1e-12)


def test_constants_match_the_first_order_model():
    assert core.E_ELEC == 50e-9
    assert core.EFS == 10e-12
    assert core.EMP == 0.0013e-12
    assert core.E_DA == 5e-9
    assert math.isclose(core.D0, math.sqrt(10e-12 / 0.0013e-12))
    assert 87.7 < core.D0 < 87.71


def test_free_space_term_below_the_crossover_and_multipath_above_it():
    below, above = 87.0, 100.0
    assert below < core.D0 < above
    assert radio_cost(4000, below) == 4000 * (50e-9 + 10e-12 * below ** 2)
    assert radio_cost(4000, above) == 4000 * (50e-9 + 0.0013e-12 * above ** 4)


def test_cost_is_continuous_at_the_crossover():
    assert math.isclose(radio_cost(4000, core.D0 - 1e-9), radio_cost(4000, core.D0), rel_tol=1e-9)


def test_cost_grows_with_distance_and_with_bits():
    assert radio_cost(4000, 10) < radio_cost(4000, 20) < radio_cost(4000, 120)
    assert math.isclose(radio_cost(8000, 20), 2 * radio_cost(4000, 20))


def test_aggregation_costs_5_nj_per_bit_per_signal():
    assert aggregation_cost(4000, 10) == 5e-9 * 4000 * 10
    assert aggregation_cost(4000, 0) == 0.0


def _two_sensor_net(p, seed=1):
    """Two sensors 20 m apart with plenty of energy; measured links with p(0 -> 1) = p."""
    prob = np.zeros((3, 3))
    prob[0, 1] = p
    return Network([[0.0, 0.0], [20.0, 0.0]], [100.0, 0.0], "measured", prob,
                   Params(e_init=1e9), seed=seed)


def test_probability_one_half_gives_about_two_attempts_over_10000_draws():
    net = _two_sensor_net(0.5)
    for _ in range(10000):
        net.send(0, 1)
    mean_attempts = net.attempts_total / net.hops_attempted
    expected = (1 - 0.5 ** 8) / 0.5          # 1.992 with at most 8 attempts
    assert abs(mean_attempts - expected) < 0.05
    assert abs(mean_attempts - 2.0) < 0.1
    assert net.hops_attempted == 10000


def test_every_attempt_pays_transmit_and_receive_and_nothing_for_acknowledgements():
    net = _two_sensor_net(0.5)
    for _ in range(2000):
        net.send(0, 1)
    tx = radio_cost(core.PACKET_BITS, 20.0)
    rx = rx_cost(core.PACKET_BITS)
    assert math.isclose(net.spent_tx, net.attempts_total * tx, rel_tol=1e-9)
    assert math.isclose(net.spent_rx, net.attempts_total * rx, rel_tol=1e-9)
    assert net.spent_agg == 0.0
    assert math.isclose(net.total_energy_spent, net.attempts_total * (tx + rx), rel_tol=1e-9)
