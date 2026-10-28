# Design note: what each step of the ladder isolates, and predictions

<!-- Answer every question under its **Answer:** line. Keep the ## headings as they are: the review finds your answers by them. -->

## Q1

In two or three sentences each, what do LEACH, HEED, PEGASIS, R-LEACH and ECH do?

**Answer:**

**LEACH.** In every round each sensor draws a random number and becomes a cluster head if it is below the threshold `T(n) = p / (1 - p * (r mod 1/p))`. Only nodes that have not been a head in the last 1/p rounds can be picked, so the role rotates. The other sensors join the nearest head, the heads combine their members' packets, and each head sends the result straight to the sink in one long hop.

**HEED.** Cluster heads are elected over a few fixed iterations. Each sensor starts with a probability of `C_prob` times its residual energy over its initial energy (never below a small floor), doubles it every iteration and announces itself as a head when a random draw succeeds. A sensor that hears several heads joins the one with the lowest communication cost, so nodes with more energy left are favoured and the election always finishes in a bounded number of rounds of messages.

**PEGASIS.** There are no clusters. The sensors are linked into one chain, built greedily from the sensor farthest from the sink by always adding the nearest sensor not yet on the chain. Data is combined as it moves along the chain, and one leader per round, chosen by rotation, sends the combined packet to the sink. The chain is rebuilt when a sensor dies.

**R-LEACH.** It is LEACH with the threshold multiplied by the sensor's residual energy over its initial energy (and an optimal cluster count). Sensors with more energy left therefore become cluster heads more often, and the heads still send to the sink directly.

**ECH.** Sensors that sit close enough to overlap, within a set overlap radius, form groups and take turns sleeping: in each round only some of the group stay awake to sense and send, and the rest switch off. The cluster heads are then elected among the awake sensors, so less redundant data is sent and the sleeping sensors save energy.

## Q2

Why can a ranking change between the first two levels only come from geometry, and a change between the second and third levels only come from link loss?

**Answer:**

The first step, from random-ideal to intel-ideal, changes only where the 52 sensors are. The links stay perfect in both, so every transmission succeeds, and the radio constants, the packet size, the box, the sink and the protocol code do not change. If the ranking moves between these two levels, the only thing that differs is the geometry.

The second step, from intel-ideal to intel-measured, keeps the real positions and changes only the link model. Perfect delivery becomes the delivery probability measured between each pair of motes, with up to 8 attempts per hop, and every attempt costs transmit and receive energy. The positions, sensors, sink and protocols are the same, so a change in ranking here can only come from link loss.

For this to hold, everything else is held the same across the three levels: the same 52 sensors (mote 5 and id 0 are removed everywhere), the same 0.5-40.5 m by 1-31 m box, the same sink (mote 3 at (19.5, 19)), the same radio and energy constants, the same 4000-bit packets and 0.5 J per sensor, the same 40 evaluation seeds for every protocol, and the same rule that the protocols never see the delivery probabilities.

## Q3

Which explanations other than realism could produce a ranking change, and how does the design rule each one out?

**Answer:**

1. **The luck of one topology.** The Intel lab is a single layout, and any single random layout can reorder the protocols by chance. The design compares the Intel ranking with the rankings on each of the 40 random topologies, one by one, and claims a geometry effect only if the Intel result lies outside what 90% of those 40 topologies show (`outside_90`), not just if it differs from their average.
2. **Tuning that suits one level.** A parameter tuned for random, loss-free layouts might be a poor choice under link loss. Each tunable protocol is tuned twice, at random-ideal and at intel-measured, on three held-out seeds (101-103) that are never used for results. The intel-measured results are reported with both parameter sets, and a reversal counts only if it appears with both.
3. **A different set of sensors.** Mote 5 (nobody ever hears it) and id 0 (no coordinates) are dropped at all three levels, so every level has the same 52 sensors and the same sink.
4. **A different setting.** The usual 100-node, 100 m x 100 m layout differs in node count, area and sink position, so it is never one of the levels. It is only the separate reproduction check, and the random-ideal level is built in the Intel box with the Intel sink.
5. **Different energy bookkeeping.** All five protocols run in one simulator with one energy function, which is unit-tested against the first-order formula for a single packet before any protocol code is run, so differences between papers' simulators cannot be mistaken for differences between protocols.
6. **Protocols adapting to the links.** The protocols never see the delivery probabilities. They choose cluster heads, chains and routes from positions and energy only, so a change at level 3 is a change in how the same decisions fare on lossy links.

## Q4

Write a predicted outcome for each expected result: LEACH and R-LEACH at the measured-link level, PEGASIS at the measured-link level, ECH between the first two levels, R-LEACH versus LEACH on 100 nodes, and the null result.

**Answer:**

*Written on 2026-10-28, before any simulation has been run. These predictions repeat the directions and thresholds already dated 2026-10-26 in `milestones/m000-kickoff.md` (H1 to H4 and the null) and are not meant to change them. They are not edited after this date.*

**(a) LEACH and R-LEACH at the measured-link level (H1).** I predict that from intel-ideal to intel-measured, LEACH and R-LEACH lose more packets per joule and more half-nodes-dead rounds than HEED, PEGASIS and ECH, with a drop roughly twice the smallest drop among those three, and the lowest packet delivery ratio of the five. The reason is their long single hops from cluster head to sink: the measured probability falls from about 0.52 under 5 m to about 0.04 between 20 and 50 m, so a long hop uses many of its 8 attempts, pays transmit and receive energy each time, and still loses packets, and the radio-irregularity and packet-delivery papers say the weakest links are the long ones. The deciding number is the change in mean packets per joule and in mean half-nodes-dead round per protocol, in `results/summary_by_level.csv`. Confidence: medium, because the sink is central and the longest cluster-head hop is only about 25 m.

**(b) PEGASIS at the measured-link level (H2).** I predict PEGASIS moves up. Its win rates against LEACH and R-LEACH rise by at least 0.15 against at least one of them from intel-ideal to intel-measured, with both parameter sets for the opponents, and at least one pairwise result reverses in its favour. The reason is that its chain hops go between near neighbours, where measured delivery is best, so it wastes fewer attempts; the risk is the single leader-to-sink hop each round. The deciding number is PEGASIS's pairwise win rate and paired Wilcoxon p on the half-nodes-dead round in `results/pairwise.csv`. Confidence: medium.

**(c) ECH between the first two levels (H3).** I predict ECH changes the most from random-ideal to intel-ideal, with the largest change in mean half-nodes-dead round of the five protocols and `outside_90 = true` for at least one pair that includes ECH. The reason is that its sleep-wake groups depend directly on how close the sensors are, and the real motes sit in rooms and along walls, not uniformly, so more of them fall inside an overlap radius and can take turns sleeping. My guess for the sign is that ECH lives longer on the real layout, with low confidence. The deciding numbers are ECH's rows in `results/geometry_test.csv` and its change in mean half-nodes-dead round. Confidence: medium for "changes most".

**(d) R-LEACH versus LEACH on 100 nodes (H4).** I predict R-LEACH beats LEACH on first node dead in the 100-node, 100 m x 100 m reproduction, so the mean gap over the 40 seeds is positive, in the same direction as the published 1092 versus 1382 but with a different size, most likely smaller, about +100 to +300 rounds. The reason is that scaling the threshold by remaining energy keeps weak nodes from becoming heads, and an earlier paper (Handy et al., 2002) saw gains of about 30% in first node dead for the same idea. The published numbers come from one layout, so a 40-seed mean will not match them. The deciding number is the sign and size of the mean first-node-dead gap in `results/reference_summary.csv`. If the sign is wrong I recheck both implementations before the main grid. Confidence: high on the sign, low on the size.

**(e) The null result.** The null result is that the pairwise rankings of the five protocols are the same at all three levels within seed noise. If it holds, the field's random, loss-free convention is good enough for ranking these protocols, even though absolute lifetimes change, and that is worth reporting as evidence that the convention holds. The deciding numbers are `random_share` and `outside_90` for all 10 pairs in `results/geometry_test.csv` (the null holds for geometry if none is outside the 90% range), and the win rate and paired Wilcoxon p for all 10 pairs at intel-ideal against intel-measured with both parameter sets in `results/pairwise.csv` (it holds for link loss if no pair reverses with both). I give the full null a probability of about 25%, mainly because link loss changes the energy cost of every hop. It is more likely to hold for the geometry step than for the link-loss step.
