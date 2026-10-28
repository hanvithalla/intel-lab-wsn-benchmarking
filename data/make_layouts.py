"""Generate the random sensor layouts, one per seed.

random52      52 sensors uniform in x 0.5-40.5 m, y 1-31 m (the bounding box of the
              Intel deployment), sink at (19.5, 19) (the position of mote 3).
              Evaluation seeds 1-40 and tuning seeds 101-103. This is the
              random-ideal level of the realism ladder.
canonical100  100 sensors uniform in a 100 x 100 m field, sink at (50, 50).
              Evaluation seeds 1-40. Used only for the reproduction check of
              LEACH and R-LEACH, never in the comparison across levels.

Writes
    data/layouts/<deployment>_seedNNN.json   one file per layout
    data/layouts/index.csv                   deployment, seed, n_sensors, sink_x, sink_y
    logs/make_layouts.log

Each layout is drawn from its own numpy generator seeded with [seed, n_sensors], so
a layout depends only on its seed and deployment and is the same on every run.
"""

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "layouts"
OUT_LOG = ROOT / "logs" / "make_layouts.log"

EVAL_SEEDS = list(range(1, 41))
TUNING_SEEDS = [101, 102, 103]
DECIMALS = 3  # coordinates stored to the millimetre

DEPLOYMENTS = {
    "random52": {
        "n_sensors": 52,
        "box": {"x_min": 0.5, "x_max": 40.5, "y_min": 1.0, "y_max": 31.0},
        "sink": (19.5, 19.0),
        "seeds": EVAL_SEEDS + TUNING_SEEDS,
    },
    "canonical100": {
        "n_sensors": 100,
        "box": {"x_min": 0.0, "x_max": 100.0, "y_min": 0.0, "y_max": 100.0},
        "sink": (50.0, 50.0),
        "seeds": EVAL_SEEDS,
    },
}


def make_layout(name, seed):
    cfg = DEPLOYMENTS[name]
    box = cfg["box"]
    rng = np.random.default_rng([seed, cfg["n_sensors"]])
    x = rng.uniform(box["x_min"], box["x_max"], cfg["n_sensors"])
    y = rng.uniform(box["y_min"], box["y_max"], cfg["n_sensors"])
    sensors = [[round(float(a), DECIMALS), round(float(b), DECIMALS)] for a, b in zip(x, y)]
    for a, b in sensors:
        assert box["x_min"] <= a <= box["x_max"] and box["y_min"] <= b <= box["y_max"]
    return {
        "deployment": name,
        "seed": seed,
        "n_sensors": cfg["n_sensors"],
        "box": box,
        "sink": list(cfg["sink"]),
        "sensors": sensors,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, cfg in DEPLOYMENTS.items():
        for seed in cfg["seeds"]:
            layout = make_layout(name, seed)
            with open(OUT_DIR / f"{name}_seed{seed:03d}.json", "w") as f:
                json.dump(layout, f)
            rows.append([name, seed, layout["n_sensors"], layout["sink"][0], layout["sink"][1]])

    with open(OUT_DIR / "index.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["deployment", "seed", "n_sensors", "sink_x", "sink_y"])
        w.writerows(rows)

    lines = [f"layouts written: {len(rows)}"]
    for name, cfg in DEPLOYMENTS.items():
        n = sum(1 for r in rows if r[0] == name)
        lines.append(f"{name}: {n} layouts, {cfg['n_sensors']} sensors each, sink {cfg['sink']}, "
                     f"box x {cfg['box']['x_min']}-{cfg['box']['x_max']}, "
                     f"y {cfg['box']['y_min']}-{cfg['box']['y_max']}, seeds {cfg['seeds'][0]}-"
                     f"{cfg['seeds'][-1]} ({len(cfg['seeds'])} seeds)")
    lines.append(f"evaluation seeds: {EVAL_SEEDS[0]}-{EVAL_SEEDS[-1]}; tuning seeds: {TUNING_SEEDS}")
    OUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    OUT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
