"""HEED (Younis and Fahmy, IEEE Transactions on Mobile Computing 2004, Fig. 2, p. 11 of the
Purdue copy).

Each round every sensor starts with CH_prob = max(C_prob * E_residual / E_max, p_min) and
runs the iteration of Fig. 2: a sensor that has heard no cluster head draws a random
number against CH_prob and announces itself as a tentative head, then every CH_prob
doubles, until a sensor's CH_prob has reached 1. A sensor that is still uncovered when
its CH_prob reaches 1 becomes a final head. A sensor that has not become a final head
joins the final head in range with the lowest cost, or becomes a final head itself if
there is none. Heads fuse and send straight to the sink.

The cost is the average minimum reachability power (AMRP) of the candidate head: the mean
distance from it to the sensors within the cluster range (p. 8 and p. 18). Every
sensor to sensor distance is below the crossover, so power grows with distance, and the paper
itself uses the distance as the power level (p. 18).
"""

import numpy as np

from sim.protocols import common

NAME = "heed"
DEFAULTS = {"c_prob": 0.05, "p_min": 0.0005, "cluster_radius": 25.0}


def _least_cost(cand, cost, dist):
    """For every row, the column among `cand` with the lowest cost (ties: nearest, then lowest
    index). Rows with no candidate give -1."""
    big = np.inf
    best_cost = np.where(cand, cost[None, :], big).min(axis=1)
    tied = cand & np.isclose(cost[None, :], best_cost[:, None], rtol=1e-12, atol=0.0)
    choice = np.where(tied, dist, big).argmin(axis=1)
    choice[~cand.any(axis=1)] = -1
    return choice


def setup_round(state, rng):
    cfg = state.config
    alive = state.alive_indices()
    m = len(alive)
    if m == 0:
        state.plan = common.cluster_plan(state, [], [], {})
        return state.plan
    dist = state.dmat[np.ix_(alive, alive)]
    nbr = dist <= cfg["cluster_radius"]                  # within cluster range, itself included
    others = nbr & ~np.eye(m, dtype=bool)
    counts = others.sum(axis=1)
    cost = np.where(counts > 0, (dist * others).sum(axis=1) / np.maximum(counts, 1), 0.0)   # AMRP
    ch_prob = np.minimum(1.0, np.maximum(cfg["c_prob"] * state.energy[alive] / state.e_init, cfg["p_min"]))

    in_s = np.zeros(m, dtype=bool)        # tentative or final cluster heads announced so far
    final = np.zeros(m, dtype=bool)
    done = np.zeros(m, dtype=bool)
    me = np.arange(m)
    iterations = 0
    while not done.all():
        iterations += 1
        draws = rng.random(m)
        active = ~done
        cand = nbr & in_s[None, :]
        covered = cand.any(axis=1)
        best = _least_cost(cand, cost, dist)
        at_one = ch_prob >= 1.0
        i_am_best = covered & (best == me)
        uncovered = active & ~covered
        final_now = (active & i_am_best & at_one) | (uncovered & at_one)
        tentative_now = uncovered & ~at_one & (draws <= ch_prob)
        final |= final_now
        in_s |= final_now | tentative_now
        done |= active & at_one                          # CH_previous = 1: stop after this pass
        ch_prob = np.minimum(ch_prob * 2.0, 1.0)
    state.stats["heed_iterations_max"] = max(state.stats["heed_iterations_max"], iterations)

    # phase III: join the least-cost final head in range, or become a final head
    final_in_range = nbr & final[None, :]
    has_final = final_in_range.any(axis=1)
    heads_mask = final | ~has_final
    members = ~heads_mask
    choice = _least_cost(final_in_range, cost, dist)      # only heads that were already final
    assign = {int(alive[v]): int(alive[choice[v]]) for v in np.flatnonzero(members)}
    heads = [int(alive[h]) for h in np.flatnonzero(heads_mask)]
    state.stats["heads_total"] += len(heads)
    state.plan = common.cluster_plan(state, alive, heads, assign)
    return state.plan


def route(state):
    return common.cluster_route(state)
