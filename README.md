# intel-lab-wsn-benchmarking

Wireless sensor network papers almost always compare clustering protocols on a random 100-node layout where every radio link works perfectly. This project asks whether the ranking those papers report still holds on a real deployment. We rebuild five well-known protocols (LEACH, HEED, PEGASIS, R-LEACH and ECH) in one shared Python simulator and run them on the same 52 sensors at three levels: random positions with perfect links, the real Intel Berkeley Lab positions with perfect links, and those real positions where each transmission succeeds with the delivery probability measured between the two motes (up to 8 attempts). Because each step changes one thing, any change in how long each protocol keeps the network alive and how many packets it delivers can be blamed on either real geometry or real link loss, and if nothing changes, the field's usual simulation setting is shown to be good enough for ranking these protocols.

## Layout

- `src/` simulator and protocol code
- `setup/` Colab setup check (`check_setup.ipynb`, `setup.log`, `download_check.csv`)
- `logs/`, `results/`, `figures/` run logs, result tables and plots
- `milestones/` written deliverables
- `data/` the deployment scripts and the files they generate; only `data/raw/` (the downloads) is git-ignored

## Data

The Intel Berkeley Research Lab `connectivity.txt` and `mote_locs.txt` come from https://db.csail.mit.edu/labdata/labdata.html. The data may be used in any venue with acknowledgement of Bodik, Hong, Guestrin, Madden, Paskin and Thibaux. The raw downloads go in `data/raw/` and are not committed.

- `python data/build_deployments.py` parses the Intel files and writes `data/intel.json` (52 sensors, the sink, the delivery-probability matrix), `results/link_by_distance.csv`, `figures/intel_layout.png` and `logs/build_deployments.log`.
- `python data/make_layouts.py` writes the 83 random layouts in `data/layouts/` and `data/layouts/index.csv`.
