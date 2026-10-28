"""End-to-end pilot: the five protocols at the three levels on seed 1 (15 runs).

Writes
    results/pilot_runs.csv           one row per run
    figures/pilot_alive/*.png        alive sensors against the round, one plot per run
    logs/pilot/*.log                 one log per run (settings, summary, checks, protocol counters)

The settings are not tuned: LEACH p = 0.05, R-LEACH p = 0.05, HEED C_prob = 0.05, ECH overlap
radius 8 m. Every run checks that the alive count never rises and that no energy goes negative,
and times the milliseconds per round (wall clock of the whole run divided by its rounds, fastest of
3 identical repeats).

Seeds (all randomness is seeded, and the seed is recorded):
    Every run uses SEED = 1 (below). It is passed to Network(..., seed=SEED), which builds two
    independent numpy generators from numpy.random.SeedSequence(seed): one for link outcomes and
    one for the protocol's random choices (sim/core.py, Network.__init__). The protocol files and
    this script contain no other random source (tests/test_toy.py scans them for that). The seed
    is the `seed` column of results/pilot_runs.csv and the first line of every run log.

Alive-count check (answerable from text, without opening the plots):
    After every run the script tests that the alive count never rises from one round to the next
    (`alive`) and that it falls over the run (`falls`), and writes `check alive count never rises:
    passed` (or failed) to the run log in logs/pilot/. The plots in figures/pilot_alive/ draw the
    same per-round alive counts that these checks read.

Run from the repository root:  python scripts/pilot.py
"""

import csv
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sim import protocols
from sim.core import Network, run_simulation

SEED = 1
PROTOCOLS = ["leach", "heed", "pegasis", "rleach", "ech"]
LEVELS = ["random-ideal", "intel-ideal", "intel-measured"]
CONFIG = {
    "leach": {"p": 0.05},
    "rleach": {"p": 0.05},
    "heed": {"c_prob": 0.05},
    "pegasis": {},
    "ech": {"overlap_radius": 8.0},
}
TIMING_REPEATS = 3
COLUMNS = ["protocol", "level", "seed", "status", "stopped_round", "stop_reason", "ms_per_round",
           "fnd", "hnd", "lnd", "packets_delivered", "min_energy"]

RUNS_CSV = ROOT / "results" / "pilot_runs.csv"
PLOT_DIR = ROOT / "figures" / "pilot_alive"
LOG_DIR = ROOT / "logs" / "pilot"

# plot style: one series, one hue (reference palette, light surface)
SURFACE, INK, INK_2, GRID, LINE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"


def build_network(level, seed):
    if level == "random-ideal":
        return Network.from_layout_file(ROOT / "data" / "layouts" / "random52_seed001.json", seed=seed)
    mode = "ideal" if level == "intel-ideal" else "measured"
    return Network.from_intel_file(ROOT / "data" / "intel.json", mode, seed=seed)


def plot_alive(result, protocol, level, path):
    rounds = [row["round"] for row in result.rows]
    alive = [row["alive"] for row in result.rows]
    s = result.summary
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=130, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.plot(rounds, alive, color=LINE, linewidth=2, solid_capstyle="round")
    ax.set_xlim(0, max(rounds))
    ax.set_xlabel("round", color=INK_2)
    ax.set_ylabel("sensors alive", color=INK_2)
    ax.set_title("%s at %s, seed %d: sensors alive per round" % (protocol, level, SEED),
                 color=INK, fontsize=10, loc="left")
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=8)
    # direct labels for the three lifetime numbers: FND above the flat part of the line, HND above-right, LND above-left
    ax.set_ylim(-0.06 * s["n_sensors"], s["n_sensors"] * 1.08)
    placement = {"FND": ((-6, 10), "right"), "HND": ((8, 8), "left"), "LND": ((-8, 24), "right")}
    for label, rnd in (("FND", s["fnd"]), ("HND", s["hnd"]), ("LND", s["lnd"])):
        if rnd is None:
            continue
        y = alive[rnd - 1]
        ax.plot([rnd], [y], marker="o", markersize=6, color=LINE, markeredgecolor=SURFACE,
                markeredgewidth=2, clip_on=False)
        offset, align = placement[label]
        ax.annotate("%s %d" % (label, rnd), (rnd, y), textcoords="offset points", xytext=offset,
                    ha=align, color=INK, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def write_log(path, protocol, level, config, row, result, runner, checks, error=None, timings=None):
    lines = ["pilot run: %s at %s, seed %d" % (protocol, level, SEED),
             "settings (not tuned): %s" % (config or "none"),
             "status: %s" % row["status"]]
    if error:
        lines += ["error:", error]
    if result is not None:
        s = result.summary
        lines += [
            "stopped_round: %s (%s)" % (s["stopped_round"], s["stop_reason"]),
            "fnd: %s   hnd: %s   lnd: %s" % (s["fnd"], s["hnd"], s["lnd"]),
            "packets_generated: %d   packets_delivered: %d   pdr: %.4f" % (
                s["packets_generated"], s["packets_delivered"], s["pdr"]),
            "energy_spent_j: %.6f   packets_per_joule: %.4f" % (s["energy_spent"], s["packets_per_joule"]),
            "energy_tx / rx / agg (j): %.6f / %.6f / %.6f" % (s["energy_tx"], s["energy_rx"], s["energy_agg"]),
            "hop_attempts: %d   hops_attempted: %d   hops_delivered: %d" % (
                s["hop_attempts"], s["hops_attempted"], s["hops_delivered"]),
            "min_energy_j: %.3e" % row["min_energy"],
            "ms_per_round: %.3f (fastest of %d repeats; all repeats in ms per round: %s)" % (
                row["ms_per_round"], len(timings), ", ".join("%.3f" % (1000.0 * t / s["stopped_round"]) for t in timings)),
            "protocol counters: %s" % (runner.stats or "none"),
            "check alive count never rises: %s" % ("passed" if checks["alive"] else "failed"),
            "check no energy below zero: %s" % ("passed" if checks["energy"] else "failed"),
            "check alive count falls over the run: %s" % ("passed" if checks["falls"] else "failed"),
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for level in LEVELS:
        for protocol in PROTOCOLS:
            config = CONFIG[protocol]
            row = {"protocol": protocol, "level": level, "seed": SEED, "status": "failed",
                   "stopped_round": "", "stop_reason": "", "ms_per_round": "", "fnd": "", "hnd": "",
                   "lnd": "", "packets_delivered": "", "min_energy": ""}
            result, runner, checks, error, timings = None, None, {}, None, []
            try:
                # the run is deterministic, so it is repeated and the fastest wall-clock time is kept:
                # a loaded laptop makes single timings two to ten times too slow
                timings = []
                for repeat in range(TIMING_REPEATS):
                    net = build_network(level, SEED)
                    runner = protocols.make(protocol, config)
                    start = time.perf_counter()
                    run = run_simulation(net, runner, meta={"level": level, "param_set": "pilot"})
                    timings.append(time.perf_counter() - start)
                    if repeat == 0:
                        result = run
                        first_net, first_runner = net, runner
                    else:
                        assert run.summary["fnd"] == result.summary["fnd"] and run.rows == result.rows
                net, runner = first_net, first_runner
                elapsed = min(timings)
                s = result.summary
                alive = [r["alive"] for r in result.rows]
                checks = {
                    "alive": all(b <= a for a, b in zip(alive, alive[1:])),
                    "energy": runner.min_energy >= 0.0 and float(net.energy.min()) >= 0.0,
                    "falls": alive[-1] < alive[0],
                }
                row.update(status="completed", stopped_round=s["stopped_round"], stop_reason=s["stop_reason"],
                           ms_per_round=round(1000.0 * elapsed / s["stopped_round"], 3),
                           fnd=s["fnd"] if s["fnd"] is not None else "",
                           hnd=s["hnd"] if s["hnd"] is not None else "",
                           lnd=s["lnd"] if s["lnd"] is not None else "",
                           packets_delivered=s["packets_delivered"], min_energy=runner.min_energy)
                if not all(checks.values()):
                    row["status"] = "failed"
                    error = "a check failed: %s" % checks
                plot_alive(result, protocol, level, PLOT_DIR / ("%s_%s_seed%d.png" % (protocol, level, SEED)))
            except Exception:
                error = traceback.format_exc()
            write_log(LOG_DIR / ("%s_%s_seed%d.log" % (protocol, level, SEED)), protocol, level, config, row,
                      result, runner, checks, error, timings)
            rows.append(row)
            print("%-8s %-15s %-9s rounds=%-6s ms/round=%s" % (
                protocol, level, row["status"], row["stopped_round"], row["ms_per_round"]))
    with open(RUNS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
