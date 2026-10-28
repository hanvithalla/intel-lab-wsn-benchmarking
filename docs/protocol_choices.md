# Protocol choices: what each paper leaves unstated, and what the simulator does

Every protocol is rebuilt in `sim/protocols/` (one file each) and runs on the one simulator in `sim/core.py`. Where a paper leaves a detail open, the simplest reading was chosen, written down here with the page being read, and used at every level (random-ideal, intel-ideal, intel-measured, and the 100-node reproduction). No choice was picked by looking at which one gave a nicer result: each file was written once from these readings, and the only change made after the first run is the one listed at the end.

**How pages are given.** The page is the PDF page of the copy listed in `papers/README.md`: the HICSS 2000 LEACH paper (10 pages), the 2002 TWC paper (11 pages), the HEED paper from the authors' Purdue page (36 pages, double spaced), R-LEACH from arXiv 1902.01445 (8 pages), and ECH from the IEEE Access PDF in `papers/`, where the printed page numbers are also given (107146 is PDF page 5). The PEGASIS copy is a 7-page hosted copy of the 2002 Aerospace paper, and the page is that copy's own page. The IEEE original of PEGASIS is paywalled, so its page numbers may differ from the printed ones.

## 1. Choices that apply to all five protocols

| # | Detail the papers leave open | Choice | Page read |
|---|---|---|---|
| C1 | Energy for control messages (advertisements, join requests, TDMA schedules, the PEGASIS token, ECH update packets) | Not charged, the same way acknowledgements are not charged at any level. Only data packets and data fusion cost energy. This keeps the five protocols on one footing: ECH and HEED send the most control traffic and would otherwise be penalised for something the other three do not model. | LEACH (HICSS) p. 9 describes the messages and gives no energy for them |
| C2 | What a cluster head or chain node pays to fuse | Fusing k >= 2 signals costs E_DA x bits x k, counting the node's own reading and every packet it received. A node holding one signal pays nothing to fuse. The fused packet has the same 4000 bits. | TWC p. 6 (E_DA = 5 nJ/bit/signal) |
| C3 | How a cluster head reaches the sink | One hop, straight to the sink, in every cluster protocol. Every distance in this study is below the crossover (longest 47.2 m, crossover 87.7 m), so there is no reason to relay. | HICSS p. 9; R-LEACH p. 5 ("single-hop or multi-hop"); HEED p. 8 (inter-cluster power levels); ECH p. 107147 (Eq. 18) |
| C4 | A round in which no cluster head is chosen (possible for LEACH, R-LEACH and ECH) | Every awake sensor sends straight to the sink that round. The round is counted in `state.stats["rounds_without_head"]` and reported in the run log. The papers do not say what happens. | not stated in any of the five papers |
| C5 | Ties (two heads at the same distance, two sensors with the same weight) | The lower sensor index wins, so runs are repeatable. The papers choose at random. | HICSS p. 9 and TWC p. 4 ("in the case of ties, a random cluster head is chosen") |
| C6 | When a sensor counts as dead | When its energy reaches 0. HEED's paper counts a node dead at 99.9% loss. | HEED p. 25 |
| C7 | One reading per sensor per round | Every awake sensor produces one reading per round, one data packet per round for a member, and one fused packet per round for a head. This is the study's held-fixed rule ("one packet per alive sensor per round"). ECH's sleeping sensors produce nothing, so for ECH `packets_generated` is smaller than for the others and delivery must be read beside lifetime. | study design note; ECH p. 107146 |
| C8 | Round length and frames per round | One round is one set-up and one data frame. | HICSS p. 8 (the steady-state phase is long compared to the set-up phase); HEED p. 24 (clustering is triggered every T_NO TDM frames) |
| C9 | What protocols may know | Positions, residual energies, alive flags and the round number, through a `State` object that holds no reference to the network. The delivery probabilities cannot be reached from a protocol, and `tests/test_toy.py` checks that the first-round plan does not change when the probabilities change. | study design (held-fixed rules) |

## 2. LEACH (`sim/protocols/leach.py`)

| # | Detail | Choice | Page read |
|---|---|---|---|
| L1 | The set G of sensors that have not been heads in the last 1/p rounds | Epoch reading: G is refilled with every alive sensor at the start of each epoch (round r0 with r0 mod 1/p = 0, where r0 = round - 1 as the paper counts from 0). A sensor that serves leaves G until the epoch ends. This is the usual way the threshold formula is implemented. | HICSS p. 8 |
| L2 | 1/p when it is not a whole number (p = 0.03, 0.08, 0.12 are in the tuning grid) | The epoch is 1/p rounded to the nearest whole number: 33, 12 and 8 rounds. The threshold is capped at 1. | HICSS p. 8 |
| L3 | The draw | A sensor becomes a head if its random number is strictly below T(n). One draw per sensor per round, alive or not, so the random stream does not depend on who has died. | HICSS p. 8 |
| L4 | Number of clusters | Not set: it is whatever the threshold gives. p is the tuned parameter (0.03, 0.05, 0.08, 0.12). The pilot and the reproduction use p = 0.05, the value the paper uses. | HICSS p. 6 and p. 8 |
| L5 | Joining a cluster | Nearest head by distance (the paper uses signal strength, which in this study's ideal radio model is the same thing). A member never goes straight to the sink, even if the sink is nearer. | HICSS p. 9 |

## 3. R-LEACH (`sim/protocols/rleach.py`)

| # | Detail | Choice | Page read |
|---|---|---|---|
| R1 | Round 1 | LEACH threshold (Eq. 4), as the paper says: "for the first round the clusters and CHs are formed using normal LEACH". From round 2 on, Eq. 5. | R-LEACH p. 4 |
| R2 | Eq. 5 can give a value above 1 (the LEACH threshold times E_res/E_init times k_opt, with k_opt of about 6 to 10) | The threshold is capped at 1. | R-LEACH p. 4 (no cap is stated) |
| R3 | How k_opt is computed. Eq. 6 as printed, with the Table I values, has a negative radicand: E_amp d^4 (2m-1) E_0 - m E_DA with E_amp = 0.0013 pJ/bit/m^4, E_0 = 0.5 J and E_DA = 5 nJ/bit is 1.3e-15 d^4 x 0.5 - 5e-9, which is below zero for every d under 52.7 m. The 100-node field has d_toBS of about 41 m and the Intel box about 12 m. The units also do not match (J^2/bit against J/bit) and d is not defined. | k_opt comes from the derivation Eq. 6 is taken from (TWC Eq. 19 and its free-space version): k_opt = sqrt(n / 2 pi) x M / d_toBS when the heads reach the sink in the d^2 regime, and sqrt(n / 2 pi) x sqrt(eps_fs / eps_mp) x M / d_toBS^2 in the d^4 regime. n is the number of sensors still alive, M the side of a square with the area of the box around all sensors, d_toBS the root mean square distance of the alive sensors to the sink. The value is kept between 1 and n and recomputed each round. Every level here is in the d^2 regime. | R-LEACH p. 4 (Eq. 6) and p. 5 (Table I); TWC p. 7 (Eq. 19) |
| R4 | Table I labels (the 0.0013 pJ/bit/m^4 entry is called "receiving" and a second E_amp of 100 pJ/bit/m^2 is carried over from LEACH) | Read as the standard first-order model: eps_mp = 0.0013 pJ/bit/m^4, eps_fs = 10 pJ/bit/m^2, E_elec = 50 nJ/bit. The 100 pJ/bit/m^2 amplifier of the old LEACH paper is not used anywhere. | R-LEACH p. 5 (Table I) |
| R5 | p (the paper's P) is not in Table I | p = 0.05 for the reproduction and the pilot (the LEACH value); p is tuned over 0.03, 0.05, 0.08, 0.12 in the main grid, as for LEACH. | R-LEACH p. 4 |
| R6 | The set G and the epoch | As for LEACH (L1, L2). | R-LEACH p. 4 |
| R7 | What happens when the factor E_res/E_init x k_opt shrinks the threshold, or when every sensor has served and the epoch is not over | Nothing special: those rounds have no head and every sensor sends to the sink (C4). With the readings above, 44% to 51% of the rounds of an R-LEACH run have no head on the first five 100-node layouts and 43% on the pilot run at random-ideal. This is the "stuck round" failure that Handy et al. (2002) describe for energy-weighted thresholds, and it is a property of Eq. 5 as printed, not of the simulator. It is reported in the pilot run logs and the milestone 8 pilot report so that it is not hidden. | R-LEACH p. 4; Handy et al., MWCN 2002 |

## 4. HEED (`sim/protocols/heed.py`)

| # | Detail | Choice | Page read |
|---|---|---|---|
| H1 | Which communication cost to use | AMRP of the candidate head: the mean distance from the candidate to the sensors within the cluster range. The paper itself uses distance as the power level in its simulation, and with every distance below the crossover, power grows with distance. A candidate with no neighbour has cost 0. | HEED p. 8 (cost types) and p. 18 |
| H2 | Cluster range for a small field | 25 m at every level, the smallest range the paper tests, and the only one that is not a large fraction of the 40 m x 30 m Intel box. It is not tuned (the study tunes only C_prob for HEED). | HEED p. 18 |
| H3 | p_min | 0.0005, the paper's simulation value. A sensor with very low energy then needs 12 iterations at most (the paper's Lemma 1 bound), and a test checks that. | HEED p. 18 (value), p. 11 (Lemma 1) |
| H4 | E_max | The initial energy of a sensor (0.5 J). | HEED p. 9 |
| H5 | C_prob | The study tunes it over 0.02, 0.05, 0.1, 0.2. The pilot uses 0.05 (the paper's). | HEED p. 9 and p. 25 |
| H6 | How often to re-cluster | Every round. The paper re-clusters every T_CP + T_NO seconds, and one round here is one data frame. | HEED p. 9 and p. 24 |
| H7 | Where the ElseIf on line 9 of Fig. 2 belongs | To the "If S_CH is not empty" of line 1: an uncovered sensor whose CH_prob is 1 declares itself a final head, and a covered sensor that is not its own best head does nothing in that iteration. | HEED p. 11 |
| H8 | Iterations in a network with no clocks | Synchronous: in one iteration every sensor decides from the heads announced up to the end of the previous iteration, then all new heads are announced together. A sensor stops after the iteration in which its CH_prob was 1. Every sensor draws one random number per iteration. | HEED p. 10-11 |
| H9 | How a member picks its head in phase III | The least-cost head among the heads that were already final in its range, ties by distance (H1). Sensors with no final head in range become heads themselves, all at once. | HEED p. 11 (phase III) |
| H10 | Inter-cluster routing | Not used: heads send straight to the sink (C3). | HEED p. 8 |

## 5. PEGASIS (`sim/protocols/pegasis.py`)

| # | Detail | Choice | Page read |
|---|---|---|---|
| P1 | Chain construction | Greedy, from the alive sensor farthest from the sink (lowest index on a tie). Each step appends to the end of the chain the nearest sensor that is not on it (lowest index on a tie). | PEGASIS p. 3 |
| P2 | Leader | The sensor with number "i mod N", as the paper says: with sensors that have died, N is the number of alive sensors and the leader of round r is the ((r - 1) mod N)-th alive sensor in index order. | PEGASIS p. 4 |
| P3 | The "threshold on neighbour distance" for leaders | Left out: the paper gives no value. It would only stop sensors with far chain neighbours from leading. PEGASIS has no parameter, so its `param_set` is none in every run. | PEGASIS p. 4 |
| P4 | When the chain is rebuilt | At the start of any round after a sensor has died, in the same greedy way, without the dead sensor. | PEGASIS p. 4 |
| P5 | Token passing | Not charged (C1). The data moves from both chain ends towards the leader, each sensor fusing its own reading with the packet it received, so every sensor but the two ends pays to fuse two signals and the leader three. | PEGASIS p. 4 |
| P6 | What happens at the sink | The leader sends one fused packet straight to the sink (C3). | PEGASIS p. 4 |

## 6. ECH (`sim/protocols/ech.py`)

| # | Detail | Choice | Page read |
|---|---|---|---|
| E1 | What the study's "overlap radius" (2, 4, 6, 8 m) is | The sensing radius R_sense. Two sensors are neighbours when they are within 2 R_sense (Eq. 10), so the grid gives neighbour distances of 4, 8, 12 and 16 m, and the paper's own R_sense of 10 m (Table 1) sits just above the grid. The alternative, taking the grid as the neighbour distance itself (2 to 8 m), would put every grid value far below the paper's 20 m. This reading is the one to confirm with the mentor; changing it only changes which numbers are put in the grid, not the code. The pilot uses 8 m, the grid value nearest the paper. | ECH p. 107146 (Eq. 10), p. 107150 (Table 1) |
| E2 | Which weight (of Weight1, 2, 3) sets the waiting time | Weight2 = R_sense / E(n_i): sensors decide in order of decreasing residual energy, ties by index. A sensor with more energy waits less, decides first and so tends to stay awake, which protects the weaker sensors. Weight1 needs the energy of every sensor covering each point and Weight3 adds the sink distance, and the paper does not say how the three combine. | ECH p. 107146 (Eq. 12-14), p. 107147 (Algorithm 1) |
| E3 | How "the sensing range is fully monitored" is tested | The sensing disk of a sensor is sampled at 25 points (the centre, 8 points at half the radius, 16 points on the circle). The disk counts as fully monitored when every sample point is within R_sense of some neighbour that has already announced WAKING. The disk is not clipped to the field, so a sensor at the edge, or one with few neighbours, rarely sleeps. The paper only says sensors have GPS-like localisation. | ECH p. 107146 (Eq. 11), p. 107147 (Algorithm 1 line 5) |
| E4 | Unpaired sensors | A sensor with no alive neighbour within 2 R_sense is unpaired and awake every round. A sensor whose neighbours have all died becomes unpaired. | ECH p. 107146 |
| E5 | Sleeping sensors | They sense, compute and transmit nothing and spend no energy (the paper sets E_ns = 0 J). They produce no reading, so they add nothing to `packets_generated`. | ECH p. 107147 (Eq. 22) |
| E6 | k_opt and p_opt | Eq. 23 as printed: k_opt = sqrt(2 n_active / (2 pi x 0.765)) for the n_active awake and unpaired sensors, p_opt = k_opt / n_active (Eq. 24). The formula assumes free-space (d^2) transmission to the sink, which is true everywhere in this study. | ECH p. 107147 (Eq. 23, 24) |
| E7 | The threshold Th and "has not been a head for the last rounds" | Th is the LEACH threshold built from p_opt, with r mod 1/p_opt rounded to a whole epoch. A sensor may be a candidate again only after a whole epoch (1/p_opt rounds, recomputed each round) since it was last a head. This is a rolling window rather than the fixed epoch of LEACH, because ECH's epoch length changes with the number of awake sensors. | ECH p. 107147 |
| E8 | Target number of heads | K = round(k_opt), at least 1. | ECH p. 107148 (the three cases) |
| E9 | Too few candidates (case 2) | One re-election pass: each awake non-candidate that may serve and whose mean distance to the candidates is greater than its distance to the sink draws a second random number against Th. If there are no candidates at all, every such sensor draws. After that pass the candidates are accepted, even if there are still fewer than K. | ECH p. 107148 |
| E10 | Too many candidates (Algorithm 2) and the fuzzy "chance" | The fuzzy rules are not given. Replaced by a plain score: chance = 0.5 x (E / largest E among candidates) + 0.5 x (1 - Ld / largest Ld), with Ld the sum of the distances to the other candidates (Eq. 25). The paper's direction is kept: less energy and a larger local distance make a candidate more likely to go back. The candidate with the lowest chance goes back to being a normal sensor, and the check repeats until K candidates are left. | ECH p. 107148 (Algorithm 2, Eq. 25) |
| E11 | Joining | A normal sensor sends straight to the sink if the sink is nearer than every head, otherwise it joins the nearest head. If there is no head, every awake sensor sends to the sink (C4). | ECH p. 107148 (free organisation) |
| E12 | Data size | 4000 bits (the paper uses 3000 bytes), to keep the study's held-fixed packet size. | ECH p. 107150 (Table 1) |

## 7. Pilot settings and one change

The pilot (`scripts/pilot.py`) is not tuned: LEACH p = 0.05, R-LEACH p = 0.05, HEED C_prob = 0.05, ECH overlap radius 8 m (the largest grid value, which is also the slowest for ECH, so the timing is a cautious one). The tuning in the later milestone replaces them.

The first version of `sim/protocols/heed.py` let a member join a head that had only just declared itself final in phase III. It was changed before any run to join only heads that were already final, as the paper's phase III reads. No other change was made after the first run.

A quick look at LEACH and R-LEACH on the first five 100-node layouts with these readings (p = 0.05, 0.5 J, 4000 bits, sink at the centre, not part of any deliverable and to be replaced by the 40-seed reproduction in the next milestone): first node dead at 895 rounds for LEACH against 985 for R-LEACH, last node dead at 1281 against 1584. The direction matches the paper (1092 against 1382, 1510 against 2474); the numbers do not, which is expected (one published layout, unstated settings).
