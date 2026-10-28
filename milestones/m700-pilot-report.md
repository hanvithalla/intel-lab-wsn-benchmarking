# Pilot timing and the reproduction-seed decision

<!-- Answer every question under its **Answer:** line. Keep the ## headings as they are: the review finds your answers by them. -->

## Q1

What was the mean milliseconds per round in the pilot, and which protocol and level was slowest? How many seeds will the 100-node reproduction use, and why?

<!-- Point at your own results: name the file, or quote a number from it. -->

**Answer:**

In `results/pilot_runs.csv` the mean over the 15 runs is **0.98 ms per round** (the round-weighted mean is 0.96 ms). The slowest run was **ECH at random-ideal, 2.41 ms per round**, followed by ECH at intel-ideal (2.00 ms) and ECH at intel-measured (1.97 ms). By protocol the means are PEGASIS 0.27 ms, R-LEACH 0.43 ms, LEACH 0.57 ms, HEED 1.53 ms and ECH 2.13 ms. By level they are 1.04 (random-ideal), 0.86 (intel-ideal) and 1.05 ms (intel-measured), so the link level makes no real difference to speed. ECH and HEED are slowest because they build neighbour sets and run several election iterations every round. Each figure is the fastest of 3 identical repeats of the run (all three are in the run logs in `logs/pilot/`).

The slowest run is about 25 times under the 60 ms limit and the mean about 50 times under the 50 ms the compute plan assumes. The 100-node reproduction runs only LEACH and R-LEACH; I timed them separately on one 100-node layout (seed 1, fastest of 3, a command I ran outside the pilot, so these numbers are not in the CSV): 0.77 ms per round for LEACH and 0.68 ms for R-LEACH. HEED and ECH at 100 nodes took 1.94 ms and 3.58 ms. The rule in the milestone only cuts seeds if rounds are slower than 60 ms, and nothing is, so **the 100-node reproduction keeps all 40 seeds (1 to 40) and nothing is cut**. A full reproduction (2 protocols x 40 seeds x about 1,500 rounds at about 1 ms) takes a few minutes.

One caution about the timing: the lifetimes are identical every time the pilot runs, but wall-clock times are not. On one earlier run, while other programs on this laptop were using about 90% of the CPU, the same ECH run took 16.7 ms per round, and an earlier quiet run gave 2.0 ms. I therefore added the three repeats, kept the fastest, and re-ran the pilot after the CPU load had settled. Even the loaded measurement of 16.7 ms is below 60 ms, so the seed decision does not depend on which one is used.

## Q2

Did any protocol fail, produce negative energy, or show alive counts that never fell? What did you change?

<!-- Point at your own results: name the file, or quote a number from it. -->

**Answer:**

No run failed: all 15 rows of `results/pilot_runs.csv` have `status = completed`, and every run ended with `stop_reason = all_dead` (none reached the 20,000-round cap, the longest was ECH at random-ideal with 1,933 rounds). `min_energy` is 0.0 in all 15 rows, so no sensor went below zero (the ledger lets a sensor use up what it has and die at exactly 0, and the toy-layout tests check this). Each run log in `logs/pilot/` records three passed checks: the alive count never rises, it falls over the run (52 at the start, 0 at the end), and no energy is below zero. The plots in `figures/pilot_alive/` show the same. Total energy spent in every run is 26.0 J, which is 52 x 0.5 J, so the ledger balances.

Three things I looked at that are not failures:

1. **R-LEACH has many rounds with no cluster head.** In its logs, 729 of 1,691 rounds at random-ideal (43%), 684 of 1,648 at intel-ideal (42%) and 405 of 645 at intel-measured (63%) have no head, against 274 of 1,529 (18%) for LEACH at random-ideal. Eq. 5 multiplies the threshold by residual energy and k_opt, so sensors are used up as heads early in each epoch and later rounds find nobody eligible; in those rounds every sensor sends straight to the sink (choice C4 in `docs/protocol_choices.md`). I did not change this: it is what the equation as printed does, it is the "stuck round" problem Handy et al. describe, and R-LEACH still outlived LEACH on all three levels in this pilot (first node dead at 1329 against 1024 at random-ideal). I recorded it in `docs/protocol_choices.md` (R7) and will watch it in the reproduction.
2. **PEGASIS has a cliff-shaped alive curve.** At random-ideal 50 of 52 sensors are alive from round 1,090 to 1,114, then 48 of them die between round 1,115 and round 1,129 (first node dead 1076, half dead 1124), and the last two sensors live on, the final one until round 1,922 (see `figures/pilot_alive/pegasis_random-ideal_seed1.png`). This fits a rotating leader that spreads the load evenly, so sensors run out at nearly the same time, but I have not tested that explanation (for example by logging each sensor's energy per round). It is not a stuck simulation, because the alive count does fall to 0.
3. **Timing varied between runs** (see Q1), but lifetimes did not: I ran the pilot several times, and every run gave identical `fnd`, `hnd`, `lnd` and `packets_delivered` for every row (the script also asserts that its three timing repeats give identical per-round traces), which is the repeatability check for the seeded runs.

What I changed during the build, in the order it happened: the first draft of HEED let a member join a head that had only just declared itself final in phase III, and I changed it, before any run, to join only heads that were already final; a test of mine ran past the round it was meant to check and I added a one-round cap to the test; and I moved the lifetime labels on the plots so they do not touch the title or the line. No protocol rule was changed after seeing pilot results.

## Q3

Compare the measured-link level with the ideal-link level on the Intel positions for one protocol in the pilot. Does the direction of change match your prediction from the design note?

<!-- Point at your own results: name the file, or quote a number from it. -->

**Answer:**

I take LEACH, the protocol H1 is about. On the Intel positions, from intel-ideal to intel-measured (`results/pilot_runs.csv` and its logs): first node dead falls from 963 to 180 rounds, half the nodes dead from 1,229 to **270** (down 78%), packets delivered from 64,025 to **6,042** (down 91%), and the packet delivery ratio from 0.994 to **0.433**. Since each run spends all 26 J, packets per joule fall by the same 91%, from 2,462 to 232. The direction matches the design note, Q4(a): LEACH loses half-nodes-dead rounds and packets per joule when the links become lossy, and the delivery ratio drops a lot. The mechanism I wrote down (hops to the sink use many of the 8 attempts and still lose packets) fits the short life of the measured run: the LEACH log at intel-measured counts 66,320 attempts for 13,741 hops, 4.8 attempts per hop, against 1.0 at intel-ideal (64,241 attempts for 64,277 hops), and only 8,402 of those hops (61%) were delivered even with 8 attempts.

The other parts of the prediction I can only read as a first look, because this is one seed and no test:

- H1 says LEACH and R-LEACH lose about twice the smallest drop among HEED, PEGASIS and ECH. In half-nodes-dead rounds the drops are LEACH 959, R-LEACH 1,124, HEED 978, PEGASIS 543 and ECH 1,115. The smallest of the three is PEGASIS at 543, so LEACH is 1.8 times it and R-LEACH 2.1 times, but HEED and ECH fall by as much as LEACH or more, so "LEACH and R-LEACH lose more than HEED, PEGASIS and ECH" does not hold for HEED and ECH on this seed.
- H1 also says LEACH and R-LEACH have the lowest delivery ratio of the five. On this seed the order at intel-measured is PEGASIS 0.370, LEACH 0.433, HEED 0.442, R-LEACH 0.562, ECH 0.642, so PEGASIS is lowest and R-LEACH is not. A fused packet that crosses the chain has to survive every hop, and a loss anywhere throws away every reading it carries.
- H2 says PEGASIS moves up. Its half-nodes-dead round is the lowest of the five at intel-ideal (1,124) and the highest at intel-measured (581, ahead of ECH 460, R-LEACH 338, HEED 287 and LEACH 270), which is the predicted direction, though its delivery ratio is the lowest.

These are one seed at one layout, with parameters that are not tuned, so they are a direction check and neither support nor refute H1 or H2. The 40-seed runs with win rates and paired Wilcoxon tests decide them, and I am not changing the dated predictions in `milestones/m400-design-note.md`.
