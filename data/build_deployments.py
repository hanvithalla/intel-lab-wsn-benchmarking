"""Parse the Intel Berkeley Research Lab files and build the Intel deployment.

Reads  data/raw/connectivity.txt  and  data/raw/mote_locs.txt  (downloaded
from https://db.csail.mit.edu/labdata/ if they are missing).

Writes
    data/intel.json                 52 sensors, the sink, the 52 x 52 delivery
                                    probability matrix and the sink column
    results/link_by_distance.csv    mean delivery probability by 5 m bin
    figures/intel_layout.png        the layout with links above 0.5 drawn
    logs/build_deployments.log      what the script did and found

Rules (see the study design):
  * line 2918 of connectivity.txt ("0 31", no probability) is skipped and logged;
  * id 0 appears only as a receiver in connectivity.txt and has no coordinates,
    so every row that mentions id 0 is dropped;
  * mote 5 is dropped (no mote ever hears it: it has no non-zero outgoing link);
  * the sink is the mote with the most incoming links of probability >= 0.1
    (ties go to the lowest id), which is mote 3 at (19.5, 19);
  * the 52 sensors are the remaining motes, i.e. all 54 located motes minus
    mote 5 and minus the sink.

Data: Intel Berkeley Research Lab sensor data, https://db.csail.mit.edu/labdata/labdata.html
Acknowledgement: Bodik, Hong, Guestrin, Madden, Paskin and Thibaux.
"""

import csv
import json
import urllib.request
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BASE_URL = "https://db.csail.mit.edu/labdata/"
FILES = ["connectivity.txt", "mote_locs.txt"]

OUT_JSON = ROOT / "data" / "intel.json"
OUT_BINS = ROOT / "results" / "link_by_distance.csv"
OUT_PLOT = ROOT / "figures" / "intel_layout.png"
OUT_LOG = ROOT / "logs" / "build_deployments.log"

DROPPED_MOTE = 5      # nobody ever hears it
SINK_MIN_PROB = 0.1   # a link counts for the sink choice if p >= this
PLOT_MIN_PROB = 0.5   # links above this are drawn
BIN_WIDTH_M = 5

_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(msg)


def fetch_if_missing():
    RAW.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        path = RAW / name
        if not path.exists():
            log(f"downloading {BASE_URL}{name}")
            urllib.request.urlretrieve(BASE_URL + name, path)
        log(f"{name}: {path.stat().st_size} bytes")


def read_locations():
    locs = {}
    for line in (RAW / "mote_locs.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) == 3:
            locs[int(parts[0])] = (float(parts[1]), float(parts[2]))
    return locs


def read_connectivity(locs):
    """Return {(sender, receiver): probability} for pairs of located motes."""
    pairs = {}
    n_id0 = 0
    n_blank = 0
    for lineno, line in enumerate((RAW / "connectivity.txt").read_text().splitlines(), 1):
        parts = line.split()
        if not parts:
            n_blank += 1
            continue
        if len(parts) != 3:
            log(f"skipped line {lineno} of connectivity.txt: {line!r} (no probability)")
            continue
        s, r, p = int(parts[0]), int(parts[1]), float(parts[2])
        if s == 0 or r == 0:
            n_id0 += 1  # id 0 has no coordinates
            continue
        if s not in locs or r not in locs:
            log(f"skipped line {lineno}: mote without coordinates ({s}, {r})")
            continue
        pairs[(s, r)] = p
    log(f"dropped {n_id0} rows that mention id 0 (no coordinates)")
    if n_blank:
        log(f"ignored {n_blank} blank line(s)")
    return pairs


def dist(locs, a, b):
    return float(np.hypot(locs[a][0] - locs[b][0], locs[a][1] - locs[b][1]))


def main():
    log("build_deployments.py: Intel Berkeley Research Lab")
    log("source: https://db.csail.mit.edu/labdata/labdata.html")
    log("acknowledgement: Bodik, Hong, Guestrin, Madden, Paskin and Thibaux")
    fetch_if_missing()

    locs = read_locations()
    log(f"motes with coordinates: {len(locs)} (ids {min(locs)}-{max(locs)})")
    pairs = read_connectivity(locs)

    all_ids = sorted(locs)
    # --- file-level checks -------------------------------------------------
    log(f"mote pairs: {len(pairs)}")
    max_p = max(pairs.values())
    log(f"max probability: {max_p:.2f}")
    off = {k: v for k, v in pairs.items() if k[0] != k[1]}
    log(f"off-diagonal pairs: {len(off)}, with probability 0: "
        f"{sum(1 for v in off.values() if v == 0)}, above 0.5: "
        f"{sum(1 for v in pairs.values() if v > 0.5)}, above 0.9: "
        f"{sum(1 for v in pairs.values() if v > 0.9)}")

    out5 = sum(1 for (s, r), p in pairs.items() if s == DROPPED_MOTE and p > 0)
    log(f"mote {DROPPED_MOTE}: non-zero outgoing links = {out5} -> dropped at every level")
    assert out5 == 0, "mote 5 is expected to have no non-zero outgoing link"

    # --- sink ---------------------------------------------------------------
    incoming = Counter()
    for (s, r), p in off.items():
        if p >= SINK_MIN_PROB:
            incoming[r] += 1
    best = max(incoming.values())
    tied = sorted(m for m, c in incoming.items() if c == best)
    sink = tied[0]  # lowest id on a tie
    log(f"sink: {sink}")
    log(f"sink coordinates: ({locs[sink][0]}, {locs[sink][1]})")
    log(f"incoming links >= {SINK_MIN_PROB}: {incoming[sink]}")
    if len(tied) > 1:
        log(f"tie at {best} incoming links between motes {tied}; lowest id chosen")

    # --- sensors ------------------------------------------------------------
    sensor_ids = [m for m in all_ids if m not in (DROPPED_MOTE, sink)]
    log(f"sensors: {len(sensor_ids)} (all {len(all_ids)} motes minus mote "
        f"{DROPPED_MOTE} and the sink, mote {sink})")
    assert len(sensor_ids) == 52

    prob_matrix = [[0.0 if a == b else pairs[(a, b)] for b in sensor_ids] for a in sensor_ids]
    sink_column = [pairs[(a, sink)] for a in sensor_ids]
    sensors = [{"id": m, "x": locs[m][0], "y": locs[m][1]} for m in sensor_ids]

    sink_d = [dist(locs, m, sink) for m in sensor_ids]
    log(f"distance to sink: min {min(sink_d):.1f} m, max {max(sink_d):.1f} m")
    no_sink = [m for m, p in zip(sensor_ids, sink_column) if p == 0]
    log(f"sink column (sensor -> sink): mean {np.mean(sink_column):.3f}; "
        f"sensors with probability 0 to the sink: {no_sink if no_sink else 'none'}")
    pm = np.array(prob_matrix)
    iu = np.triu_indices(len(sensor_ids), 1)
    log(f"asymmetry: mean |p(a->b) - p(b->a)| over sensor pairs = "
        f"{np.mean(np.abs(pm[iu] - pm.T[iu])):.3f}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump({
            "source": "https://db.csail.mit.edu/labdata/labdata.html",
            "acknowledgement": "Bodik, Hong, Guestrin, Madden, Paskin and Thibaux",
            "notes": ("prob_matrix[i][j] is the delivery probability from sensors[i] to "
                      "sensors[j] (row = sender, column = receiver, diagonal 0). "
                      "sink_column[i] is the delivery probability from sensors[i] to the sink. "
                      "Mote 5 and id 0 are dropped; the sink is not one of the 52 sensors."),
            "sensors": sensors,
            "sink": {"id": sink, "x": locs[sink][0], "y": locs[sink][1]},
            "prob_matrix": prob_matrix,
            "sink_column": sink_column,
        }, f)
    log(f"wrote {OUT_JSON.relative_to(ROOT)}")

    # --- delivery probability by distance bin --------------------------------
    # Over all directed pairs of the 54 located motes: this characterises the
    # measured file itself and reproduces the figures quoted in the study design.
    d = np.array([dist(locs, a, b) for (a, b) in off])
    p = np.array(list(off.values()))
    edges = np.arange(0, np.ceil(d.max() / BIN_WIDTH_M) * BIN_WIDTH_M + BIN_WIDTH_M, BIN_WIDTH_M)
    OUT_BINS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_BINS, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["distance_bin_m", "n_pairs", "mean_prob"])
        for lo, hi in zip(edges[:-1], edges[1:]):
            sel = (d >= lo) & (d < hi)
            if sel.any():
                w.writerow([f"{int(lo)}-{int(hi)}", int(sel.sum()), round(float(p[sel].mean()), 4)])
    log(f"wrote {OUT_BINS.relative_to(ROOT)} (directed pairs of the {len(all_ids)} located "
        f"motes, longest distance {d.max():.1f} m)")
    log(f"mean probability under 5 m: {p[d < 5].mean():.2f}; "
        f"between 20 and 50 m: {p[(d >= 20) & (d < 50)].mean():.2f}")
    used = [m for m in all_ids if m != DROPPED_MOTE]
    du = np.array([dist(locs, a, b) for a in used for b in used if a != b])
    pu = np.array([pairs[(a, b)] for a in used for b in used if a != b])
    log(f"for the {len(used)} motes of the deployment (52 sensors and the sink): "
        f"under 5 m {pu[du < 5].mean():.2f}, 20-50 m {pu[(du >= 20) & (du < 50)].mean():.2f}")

    # --- plot ---------------------------------------------------------------
    deploy = sensor_ids + [sink]
    segs, strengths = [], []
    for i, a in enumerate(deploy):
        for b in deploy[i + 1:]:
            q = max(pairs[(a, b)], pairs[(b, a)])
            if q > PLOT_MIN_PROB:
                segs.append([locs[a], locs[b]])
                strengths.append(q)
    n_dir = sum(1 for a in deploy for b in deploy if a != b and pairs[(a, b)] > PLOT_MIN_PROB)
    log(f"links above {PLOT_MIN_PROB}: {n_dir} directed pairs, {len(segs)} drawn "
        f"(a line is drawn if either direction is above {PLOT_MIN_PROB})")

    fig, ax = plt.subplots(figsize=(10, 7.2))
    lc = LineCollection(segs, array=np.array(strengths), cmap="viridis", linewidths=1.0,
                        alpha=0.7, clim=(PLOT_MIN_PROB, 0.85))
    ax.add_collection(lc)
    ax.scatter([locs[m][0] for m in sensor_ids], [locs[m][1] for m in sensor_ids],
               s=26, c="black", zorder=3, label=f"{len(sensor_ids)} sensors")
    for m in sensor_ids:
        ax.annotate(str(m), locs[m], textcoords="offset points", xytext=(3, 3), fontsize=6)
    ax.scatter(*locs[sink], marker="*", s=260, c="red", edgecolor="black", zorder=4,
               label=f"sink (mote {sink})")
    ax.scatter(*locs[DROPPED_MOTE], marker="x", s=60, c="grey", zorder=3,
               label=f"mote {DROPPED_MOTE} (dropped)")
    ax.set_xlim(-1, 42)
    ax.set_ylim(-1, 32)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Intel Berkeley Research Lab: sensors, sink and links with "
                 f"delivery probability > {PLOT_MIN_PROB}")
    fig.colorbar(lc, ax=ax, shrink=0.8, label="delivery probability (larger of the two directions)")
    ax.legend(loc="center", bbox_to_anchor=(0.32, 0.5), fontsize=8)
    ax.text(0.01, -0.12, "Data: Intel Berkeley Research Lab (Bodik, Hong, Guestrin, Madden, "
            "Paskin, Thibaux), db.csail.mit.edu/labdata", transform=ax.transAxes, fontsize=7)
    OUT_PLOT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PLOT, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"wrote {OUT_PLOT.relative_to(ROOT)}")

    OUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    OUT_LOG.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
