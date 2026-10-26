# m000-kickoff: Project explained back, and dated predictions

**Project:** LEACH, HEED, PEGASIS, R-LEACH and ECH on the Intel Berkeley Lab's measured topology
**Date written:** 2026-10-26 (predictions in Q6 are frozen as of this date and must not be edited later)

**Warm-up (one sentence):** Does the ranking of five well-known sensor-network clustering protocols, as reported on random layouts with perfect links, still hold on the real Intel Berkeley Lab deployment, and if it changes, is real geometry or real link loss the cause?

---

## Q1. The project explained to a friend (max 150 words)

Sensor networks are lots of tiny battery-powered devices that send readings to one collection point. Clustering protocols decide which devices pass data along, so the batteries last longer. Almost every paper tests these protocols on a made-up random layout where every radio message always arrives. I run five well-known protocols (LEACH, HEED, PEGASIS, R-LEACH and ECH) in one shared simulator and measure how long the network stays alive and how many packets are delivered. Then I repeat it with the real sensor positions from the Intel Berkeley Lab, and finally with the message loss that was actually measured between those sensors. Each step changes only one thing. So if the ranking of the protocols changes, I can say whether real positions or real message loss caused it. If the ranking doesn't change, the field's usual simple test setup is good enough.

---

## Q2. The three levels and what each step isolates

All three levels use the **same 52 sensors** (Intel motes, with mote 5 dropped everywhere because nobody ever hears it), the same box (0.5-40.5 m by 1-31 m), the same sink (mote 3 at (19.5, 19)), the same energy constants and the same 40 evaluation seeds.

| Level | Positions | Links |
|---|---|---|
| 1. random-ideal | 52 sensors uniformly at random in the Intel box (one layout per seed) | every transmission succeeds |
| 2. intel-ideal | the real Intel mote coordinates | every transmission succeeds |
| 3. intel-measured | the real Intel mote coordinates | each attempt succeeds with the delivery probability measured for that sender and receiver, up to 8 attempts per hop, every attempt costs transmit and receive energy |

**Step 1 to 2 (random-ideal to intel-ideal).**
- *Changes:* only the positions, from random draws to the real layout.
- *Stays the same:* node count, box, sink, links (perfect), radio constants, tuned parameters, seeds.
- *Blame:* a ranking change here can only be due to **geometry**.

**Step 2 to 3 (intel-ideal to intel-measured).**
- *Changes:* only the links. Perfect delivery becomes the measured delivery probability with up to 8 attempts.
- *Stays the same:* the positions and everything else above.
- *Blame:* a ranking change here can only be due to **link loss**.

**Important at every level:** the protocols choose cluster heads, chains and routes from positions and energy only. They **never see the delivery probabilities**. So any difference at level 3 comes from the protocols' unchanged choices meeting weak links, not from the protocols adapting to them.

The 100-node, 100 x 100 m layout is not a level. It is a separate reproduction check, because it differs in node count, area and sink position and would mix several changes into one step.

---

## Q3. Average attempts on a link with p = 0.5, capped at 8

**B: about 2.**
Expected attempts with a cap of 8 are (1 - 0.5^8) / 0.5 = 0.996 / 0.5 ≈ 1.99.

---

## Q4. Which change would break the realism ladder?

**A: using the 100-node, 100 x 100 m layout as the random-ideal level.**
Node count, area and sink position would all change along with the positions, so the first step would change more than geometry and could no longer be blamed on geometry alone. B, C and D each keep or support the one-change-per-step rule (same seeds, same node set at every level, delivery reported beside lifetime).

---

## Q5. LEACH beats PEGASIS at intel-ideal but loses at random-ideal: what to check before claiming geometry changed the ranking

1. **Is the Intel result unusual among single random layouts, not just different from their average?** I rank the protocols on each of the 40 random-ideal topologies separately and count how many of them agree with the intel-ideal winner (`random_share`). The Intel result counts as a geometry effect only if it lies outside what 90% of those 40 topologies show (`outside_90`). One real layout is one draw, and any single random draw can also flip two protocols by luck.
2. **Is the paired difference big enough over the 40 seeds?** I compute the win rate for the pair over the 40 paired seeds and a paired Wilcoxon signed-rank test on the half-nodes-dead round, so a handful of lucky seeds don't count as a reversal.
3. **Was the comparison fair?** I confirm that both levels used the same 52 sensors, the same box, the same sink (mote 3 at (19.5, 19)) and the same tuned parameters, so that geometry is the only thing that differs and the gap cannot be put down to a different node set or tuning.

---

## Q6. Dated predictions (2026-10-26)

All five predictions are written before any simulation has run and are not to be edited afterwards. They are checked against results in m1100-analysis.

### H1 (RQ3): LEACH and R-LEACH lose the most at the measured-link level
- **Date:** 2026-10-26
- **Direction:** From intel-ideal to intel-measured, LEACH and R-LEACH lose more packets per joule and more half-nodes-dead rounds than HEED, PEGASIS and ECH. I expect their drop to be roughly twice as large as the smallest drop among the other three, and their PDR at intel-measured to be the lowest of the five.
- **Why:** Their cluster heads send straight to the sink, so each cluster head makes one long hop. Delivery probability falls with distance in the Intel data (about 0.52 under 5 m, about 0.04 between 20 and 50 m). Long hops therefore burn up to 8 attempts, each costing transmit and receive energy, and still lose many packets. Chain and relay protocols use shorter hops.
- **Deciding number:** The change in mean packets per joule and in mean half-nodes-dead round per protocol from intel-ideal to intel-measured in `results/summary_by_level.csv`, with PDR at intel-measured.
- **Confidence:** medium. The sink is central (mote 3), so even long cluster-head hops are at most about 25 m, and the effect may be smaller than I expect.

### H2 (RQ2): PEGASIS moves up the ranking at the measured-link level
- **Date:** 2026-10-26
- **Direction:** PEGASIS's win rates against LEACH and R-LEACH are higher at intel-measured than at intel-ideal, with both tuned parameter sets (tuned_l1 and tuned_l3 for the opponents). I expect it to gain at least 0.15 in win rate against at least one of them, and at least one pairwise result to reverse in its favour.
- **Why:** Its chain hops are between near neighbours, where measured delivery is highest (about 0.5), so it wastes fewer attempts than protocols with long hops. The one long hop per round, from the chain leader to the sink, is the main thing that could weaken this.
- **Deciding number:** PEGASIS's pairwise win rate and paired Wilcoxon p on the half-nodes-dead round, intel-ideal against intel-measured, in `results/pairwise.csv`. A reversal counts only if it holds with both parameter sets.
- **Confidence:** medium.

### H3 (RQ1): ECH changes the most between random-ideal and intel-ideal
- **Date:** 2026-10-26
- **Direction:** ECH shows the largest change in mean half-nodes-dead round from random-ideal to intel-ideal of the five protocols, and at least one of the pairs involving ECH has `outside_90 = true` in the geometry test. My guess for the sign is that ECH lives longer on the real layout, because real motes sit in rooms and along walls, so more of them fall within the overlap radius and can take turns sleeping.
- **Why:** ECH's sleep-wake rule depends directly on how close sensors are to each other. The other four protocols mostly use distances to the sink or to the nearest cluster head.
- **Deciding number:** ECH's rows in `results/geometry_test.csv` (`random_share`, `outside_90`) and its change in mean half-nodes-dead round from random-ideal to intel-ideal.
- **Confidence:** medium for "ECH changes most", low for the direction of the change.

### H4 (RQ4): R-LEACH beats LEACH on first node dead in the 100-node reproduction
- **Date:** 2026-10-26
- **Direction:** R-LEACH has the later mean first-node-dead round over the 40 reference seeds, so the gap is positive (same direction as the published 1092 for LEACH versus 1382 for R-LEACH). I expect the margin to differ from the published 290 rounds, most likely smaller, in the range of about +100 to +300 rounds.
- **Why:** R-LEACH scales the cluster-head chance by remaining energy, so weak nodes are picked less often and the first death comes later. The published numbers come from one layout with no repetitions, and a 40-seed mean will not match one layout exactly.
- **Deciding number:** The sign and size of the mean first-node-dead gap between R-LEACH and LEACH in `results/reference_summary.csv`, compared with R1. If the sign is wrong I stop and recheck both implementations before the main grid.
- **Confidence:** high on the sign, low on the size.

### Null result: the rankings do not change
- **Date:** 2026-10-26
- **Statement:** The pairwise rankings of the five protocols are the same at all three levels within seed noise. Absolute lifetimes may drop at the measured-link level, but no pairwise reversal passes the tests.
- **If it happens:** The field's random, loss-free convention is good enough for ranking these protocols, which is publishable as evidence that the convention holds.
- **Deciding numbers:** For geometry, `random_share` and `outside_90` for all 10 pairs in `results/geometry_test.csv` (the null holds if none is outside the 90% range). For link loss, the win rate and paired Wilcoxon p for all 10 pairs at intel-ideal against intel-measured with both parameter sets in `results/pairwise.csv` (the null holds if no pair reverses with both).
- **My belief:** I think the null is unlikely to hold fully at level 3 (maybe 25%), because link loss changes how many attempts and how much energy each hop costs. I think it is more likely to hold at level 2, because the Intel box is small and the layout may behave like a typical random draw for most pairs.
