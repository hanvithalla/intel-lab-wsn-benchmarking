# Related-work notes on six radio-realism and lifetime papers

<!-- Answer every question under its **Answer:** line. Keep the ## headings as they are: the review finds your answers by them. -->

## Q1

For 'Low energy adaptive clustering hierarchy with deterministic cluster-head selection': what does the paper do, what did it find, and how does it bear on this study?

**Answer:**

*(Handy, Haase and Timmermann, University of Rostock, IEEE MWCN 2002.)*

**What it does.** It changes how LEACH picks cluster heads. It first shows with a small example (20 nodes, P = 0.2, 100 m x 100 m) that random selection can put the heads near the edges or next to each other, which costs about three times as much transmission energy in the set-up phase as a good spread. It then scales LEACH's threshold by the node's remaining energy (its Eq. 7: `T(n)new = T(n) * E_current / E_max`). It finds that this makes the network get "stuck" after some rounds, "although there are still nodes available with enough energy to transmit data to the base station", because the threshold becomes too low for nodes with little energy. Its Eq. 8 repairs this by raising the threshold for any node that has not been a cluster head for up to 1/P rounds. It also introduces three lifetime metrics: FND (First Node Dies), HNA (Half of the Nodes Alive) and LND (Last Node Dies).

**What it found.** In its simulation (200 nodes in 200 m x 200 m, base station at (100, 300), 1 J per node, 200-bit messages, P = 0.05, compression to 5%), the Eq. 8 version improves FND by 30% and HNA by 21% over original LEACH. With the base station moved farther away, to (100, 500), the gains fall to about 25% and 18%, because most of the energy then goes into the cluster heads' transmissions to the base station. Eq. 7 and Eq. 8 do not differ significantly (inside the standard deviation).

**The lifetime metrics.** FND is the round when the first node dies, meant for uses where every node matters, such as intrusion or fire detection. HNA is the round when half the nodes are still alive, meant for dense deployments where losing a few nodes does not hurt the service. LND is the round when the last node dies. The authors note that for LEACH-type protocols LND "is not interesting since more than one node is necessary to perform the clustering algorithm", so they only discuss FND and HNA.

**How it bears on this study.**
- This study reports the same three measures (first, half and last node dead, FND, HND, LND) and uses the half-nodes-dead round for the pairwise tests. That matches the paper's view that the half-way point is the more robust choice for clustering protocols, and it explains why LND is read with care.
- The idea behind R-LEACH, multiplying the LEACH threshold by residual over initial energy, already appears here as Eq. 7, so R-LEACH is not a new idea. The paper also warns about a failure mode: late in a run, when most nodes have low energy, the threshold can be so low that few or no cluster heads are elected. The implementation should record how many rounds have no cluster head, and any fallback used must be written down, because it will affect R-LEACH's LND and its comparison with LEACH.
- It also supports the expected direction in the 100-node reproduction (R-LEACH should outlast LEACH on first node dead), and its result that the gain shrinks as the sink moves away fits the idea that long hops to the sink dominate energy.

## Q2

For 'Performance Analysis of Cluster-Based Routing Protocols under Propagation and Mobility Variants in Wireless Sensor Networks': what does the paper do, what did it find, and how does it bear on this study?

**Answer:**

*(Kaushik, Jain, Gunjan, Jhamb and Sharma, IEEE IC2SDT 2025. Source note: the full PDF is behind the IEEE paywall and could not be obtained, so this note is based on the published abstract only.)*

**What it does.** It compares LEACH with DCREA while varying the analytic energy model and the sink. The three energy models are the First-Order Radio Energy Model, the Free Space Path Loss Model and the Two-Ray Ground Reflection Model. The sink is either static, placed at different locations, or mobile, moving with random or grid mobility. The measures are First Node Dead (FND) and Last Node Dead (LND), for stability and lifetime.

**What it found.** DCREA beats LEACH in all scenarios, in energy efficiency and in network longevity. The biggest gains are in the mobile-sink scenarios and under the more realistic propagation model, Two-Ray Ground Reflection.

**How it bears on this study.** It is the closest earlier comparison, and it shows that the choice of analytic energy model changes how much a protocol gains. What it does not do is test the models against a measured deployment. Its energy models are all analytic, and it runs on synthetic layouts with no measured links: the abstract mentions no real mote positions or measured link delivery, and this project's own literature search describes the paper the same way (synthetic layouts, no measured links). I could not check the layout details in the full text. It also compares only two protocols, and it does not ask whether the ranking of the protocols survives a change of setting. This study differs in all of these ways. It runs five protocols, it holds the radio model fixed (first-order, so no model variation) and varies the deployment instead, from random positions, to the real Intel positions, to the Intel positions with measured delivery probabilities, and it tests the ranking with 40 seeds per condition.

## Q3

For 'Experimental evaluation of wireless simulation assumptions': what does the paper do, what did it find, and how does it bear on this study?

**Answer:**

*(Kotz, Newport, Gray, Liu, Yuan and Elliott, MSWiM 2004; extended as Dartmouth TR2004-507.)*

**What it does.** It reviews six assumptions ("axioms") that many ad hoc network simulations still make: the world is flat; a radio's transmission area is circular; all radios have equal range; if I can hear you, you can hear me; if I can hear you at all, I can hear you perfectly; and signal strength is a simple function of distance. It tests them on measurements from a large outdoor experiment, 33 laptops with WiFi cards roaming a field for over an hour with GPS positions and broadcast beacons. It then runs the same routing code in a simulator with a best-effort stochastic model (path-loss exponent 2.8, 6 dB shadow fading), and with two progressively simpler models (no variations, and a perfect channel), to see how much each simplification changes the results. It also surveyed MobiCom and MobiHoc papers from 1995 to 2003 and found that "Simple" and "Flat Earth" radio models outnumbered "Good" ones.

**What it found.** Reception fades gradually with distance, with "no visible cliff". The probability that a beacon and its acknowledgement are both received (a symmetric link) was never much above 0.8. Individual signal strength is poorly predicted by distance, even though the average follows a power law. For AODV, the real packet delivery ratio was 42.3%, the best model gave 46.8%, and the simpler models gave significantly higher values, so they exaggerated routing performance. Its recommendations include stating assumptions, using a realistic stochastic model with asymmetric links, "explor[ing] a range of model parameters since the effect of these parameters is not uniform across protocols", and using real data as simulator input where possible.

**How it bears on this study.** It answers the general question, whether simple radio assumptions can mislead an evaluation, but for ad hoc (MANET) routing with outdoor WiFi laptops, not for clustering protocols or sensor motes. That leaves our question open. Its point that the effect is not uniform across protocols is exactly what the ranking test checks, and its recommendation to use real data as input is what the intel-measured level does with the Intel delivery table.

## Q4

For 'Impact of radio irregularity on wireless sensor networks': what does the paper do, what did it find, and how does it bear on this study?

**Answer:**

*(Zhou, He, Krishnamurthy and Stankovic, MobiSys 2004.)*

**What it does.** It measures radio irregularity on MICA2 motes and finds that the received signal strength is largely random, but changes continuously as the direction changes, and that devices differ in sending power. From this it builds the Radio Irregularity Model (RIM), controlled by a Degree of Irregularity (DOI) and a variation in sending power (VSP), and puts it into the GloMoSim simulator. It then measures the effect on MAC protocols (CSMA, 802.11 DCF) and on routing protocols (AODV, DSR and geographic forwarding, GF) in 100 nodes over 150 m x 150 m. Finally it proposes six ways to cope and evaluates two, in simulation and on a testbed.

**What it found.** Radio irregularity has a significant impact on routing protocols but a relatively small impact on MAC protocols. GF is hit hardest, losing 70% of its packets at DOI 0.01, because greedy forwarding keeps picking nodes near the edge of the range, which are most likely to have asymmetric links. AODV and DSR cope better because they try several paths, but at the cost of more control packets and more energy.

**How it bears on this study.** It is the reason for the measured-link level. If radio irregularity hurts the routing layer more than the MAC layer, then a routing or clustering comparison is the kind of study where the loss-free assumption is most likely to mislead. Its mechanism, that protocols picking the farthest neighbours meet the weakest links, is the reasoning behind hypothesis H1: LEACH and R-LEACH make long single hops from cluster head to sink. A limit to remember is that its model also covers interference and direction, whereas our measured-link level uses one averaged delivery probability per ordered pair.

## Q5

For 'Understanding packet delivery performance in dense wireless sensor networks': what does the paper do, what did it find, and how does it bear on this study?

**Answer:**

*(Zhao and Govindan, SenSys 2003.)*

**What it does.** It measures packet delivery with up to 60 Mica motes in three environments: an indoor office building, a habitat with moderate foliage, and an open parking lot. At the physical layer it uses a single sender on a line and varies transmit power and encoding. At the MAC layer it studies carrier sensing and link-layer retransmissions.

**What it found.** Packet loss has heavy tails. Indoors, "fully half of the links experienced more than 10% packet loss, and a third more than 30%". There is a "gray area" inside the communication range, in some environments almost a third of it, where reception is choppy and varies over time. Link-layer retransmissions do not remove the variability, and 50% to 80% of communication energy is wasted overcoming collisions and environmental effects. In the harsher environments nearly 10% of links lose packets asymmetrically. The authors suggest discarding poorly performing and asymmetric neighbours (topology control), and note that their data can be used as trace-driven simulation input.

**How it bears on this study.** The Intel Lab delivery table has the same shape. Of 2,916 directed mote pairs, 458 have probability 0, none exceeds 0.90, and the mean falls from 0.52 under 5 m to 0.04 between 20 and 50 m, and the probability from A to B differs from B to A. The intel-measured level uses those directional probabilities as trace-driven input, with up to 8 attempts per hop, each costing transmit and receive energy, which echoes the finding that retransmissions burn energy. A caveat is that the Intel probabilities are averages over the whole 2004 deployment, so the time variation this paper stresses is not represented.

## Q6

For 'Link-Quality-Based Energy-Efficient Routing Protocol for WSN in IoT': what does the paper do, what did it find, and how does it bear on this study?

**Answer:**

*(Shahid, Tariq, Iqbal, Albarakati, Fatima and Khan, IEEE Transactions on Consumer Electronics, 2024. Source note: the full PDF is behind the IEEE paywall and could not be obtained, so this note is based on the published abstract only.)*

**What it does.** It proposes LQEER, a routing protocol that estimates link quality and uses it together with node energy to plan routes. It uses a cost to pick the most suitable nodes for forwarding, with the aim of cutting packet loss. It is evaluated by simulation against state-of-the-art routing protocols.

**What it found.** According to the abstract, LQEER improves packet delivery ratio, lowers energy consumption and lowers end-to-end delay compared with the protocols it was tested against. The abstract gives no numbers.

**How it bears on this study.** It is an example of a protocol that sees link quality, whereas LEACH, HEED, PEGASIS, R-LEACH and ECH choose cluster heads, chains and routes from positions and energy only, and are never shown the delivery probabilities, at any level. That is deliberate. It keeps the intel-measured step a test of what link loss does to protocols that do not adapt to it. If the measured-link results show large losses for some protocols, a link-aware rule like LQEER's is the natural next thing to try, and this study's numbers would show how much there is to gain.
