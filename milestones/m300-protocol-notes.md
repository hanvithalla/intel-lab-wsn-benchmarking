# m300: Notes on the origin papers of the five protocols and the radio model

These notes feed the methods section and the protocol code in the simulator milestone. For each protocol they record how cluster heads (or the chain leader) are chosen, how data reaches the sink, the parameters the authors set, and what the paper leaves unstated.

## Q1

**Energy-efficient communication protocol for wireless microsensor networks** (Heinzelman, Chandrakasan, Balakrishnan, HICSS 2000). This is the paper that introduces LEACH.

**What it does.** It argues that direct transmission, minimum-transmission-energy (MTE) multi-hop routing and static clustering are poor choices for sensor networks. It proposes LEACH, which rotates the cluster-head role at random, and compares the four protocols in a MATLAB simulation: 100 random nodes in a 100 m x 100 m field, the base station at (0, -100) (100 m from the nearest node), 2000-bit messages, Eelec = 50 nJ/bit, and a single amplifier term of 100 pJ/bit/m² (distance squared only).

**What it found.** With 0.5 J per node, the first node dies at round 932 in LEACH against 109 for direct transmission, 8 for MTE and 80 for static clustering. The last node dies at round 1312 against 234, 429 and 110 (its Table 2). Its conclusion: "The first node death in LEACH occurs over 8 times later than the first node death in direct transmission, minimum-transmission-energy routing, and a static clustering protocol, and the last node death in LEACH occurs over 3 times later."

**How cluster heads are chosen.** At the start of each round every node draws a random number between 0 and 1. It becomes a cluster head if the number is below the threshold

```
T(n) = P / (1 - P * (r mod (1/P)))   if n is in G
T(n) = 0                              otherwise
```

where P is the desired cluster-head fraction (the paper uses P = 0.05), r is the current round, and G is the set of nodes that have not been cluster heads in the last 1/P rounds. Every node is therefore a cluster head once in 1/P rounds.

**How data reaches the sink.** Each non-head node joins the cluster whose advertisement it hears with the largest signal strength, which is normally the nearest cluster head (ties broken at random). The cluster head builds a TDMA schedule, receives from its members, aggregates, and sends one message straight to the base station (single hop). Clusters use different CDMA codes to avoid interference.

**Parameters set by the authors.** P = 0.05, Eelec = 50 nJ/bit, amplifier 100 pJ/bit/m², 2000-bit messages, 100 nodes, 0.25, 0.5 and 1 J per node.

**Left unstated or open.** The paper says "Future versions of this work will include an energy-based threshold", so it leaves energy-aware selection for later. I found no data-fusion energy value in this paper (the journal version adds 5 nJ/bit/signal) and no round length, and the results come from a single random network with no repetitions.

**How it bears on this study.** It is the baseline protocol, and p (the paper's P) is the parameter the study tunes over 0.03, 0.05, 0.08 and 0.12. In the paper the base station is 100 m away and the radio model has no distance-to-the-fourth term, so long cluster-head-to-sink hops dominate. In our study the sink is in the middle of the lab and no distance reaches the crossover.

## Q2

**An application-specific protocol architecture for wireless microsensor networks** (Heinzelman, Chandrakasan, Balakrishnan, IEEE Transactions on Wireless Communications, vol. 1, no. 4, October 2002). This is the journal version of LEACH, and it is where the radio model comes from.

**What it does.** It gives the full LEACH architecture: distributed cluster formation, the cluster-head probability, an analysis of the best number of clusters, TDMA steady-state operation, and a comparison with MTE routing, static clustering and the centralized LEACH-C in the ns simulator. The setup is 100 nodes in 100 m x 100 m, the base station at (50, 175), 500-byte data messages with 25-byte headers, 2 J per node, 5 clusters.

**What it found.** "LEACH can improve system lifetime by an order of magnitude compared with general-purpose multihop approaches." It also shows that the optimal number of clusters for 100 nodes is about 3 to 5 (its Fig. 6), and that LEACH only beats multi-hop MTE routing when cluster heads can fuse the data well.

**The first-order radio model (copied from the paper).** To send an l-bit message over distance d:

```
E_Tx(l, d) = E_Tx-elec(l) + E_Tx-amp(l, d)
           = l*E_elec + l*eps_fs*d^2      for d <  d_o          (9)
           = l*E_elec + l*eps_mp*d^4      for d >= d_o
```

To receive an l-bit message:

```
E_Rx(l) = E_Rx-elec(l) = l*E_elec                                (10)
```

with E_elec = 50 nJ/bit, eps_fs = 10 pJ/bit/m², eps_mp = 0.0013 pJ/bit/m⁴ and a data-aggregation energy E_DA = 5 nJ/bit/signal. The paper calls d_o only "a threshold" and gives no number. This study sets it where the two branches meet, d_o = sqrt(eps_fs / eps_mp) = sqrt(10 / 0.0013) ≈ 87.7 m. The longest distance between two Intel motes is 47.2 m, so the d⁴ branch is never used here. As a check, one 4000-bit packet over 20 m costs 4000 x (50e-9 + 10e-12 x 20²) = 0.000216 J to send and 4000 x 50e-9 = 0.0002 J to receive.

**Cluster-head probability (copied from the paper).** With N nodes and k expected clusters per round, the probability that node i becomes a cluster head in round r is

```
P_i(t) = k / (N - k * (r mod (N/k)))   if C_i(t) = 1   (3)
P_i(t) = 0                              if C_i(t) = 0
```

where C_i(t) = 1 only if the node has not been a cluster head in the last (r mod N/k) rounds. This is the same rule as the HICSS threshold with P = k/N. The paper adds an energy-weighted version for nodes with unequal energy:

```
P_i(t) = min{ E_i(t)/E_total(t) * k , 1 }                (6)
```

The optimal number of clusters (its Eq. 19) is `k_opt = sqrt(N)/sqrt(2*pi) * sqrt(eps_fs/eps_mp) * M / d_toBS^2`.

**How it bears on this study.** Every protocol in the simulator pays for transmission and reception from Eq. 9 and 10, so these equations are copied exactly and covered by a unit test. Eq. 6 shows that an energy-weighted cluster-head rule was proposed here years before R-LEACH. A caution: the derivation of k_opt assumes the cluster head sends to the base station in the d⁴ regime (75 m < d_toBS < 185 m in the paper). On the Intel layout every distance is below d_o, so that formula should not be applied there as it stands.

## Q3

**HEED: a hybrid, energy-efficient, distributed clustering approach for ad hoc sensor networks** (Younis and Fahmy, IEEE Transactions on Mobile Computing, 2004; read from the authors' Purdue copy).

**What it does.** It proposes HEED, which re-clusters every T_CP + T_NO seconds. Cluster heads are chosen mainly by residual energy, and a secondary cost (such as the average minimum reachability power, AMRP, or node degree) breaks ties and picks the cluster. It proves the election ends in a constant number of iterations and tests it in simulation against a generic weight-based clustering and against a generalized LEACH.

**What it found.** The election ends in N_iter <= ceil(log2(1/p_min)) + 1 iterations, which for p_min = 0.0005 is at most 12. In simulation HEED gives a longer time to first node death and to last node death than gen-LEACH, because gen-LEACH picks cluster heads at random and so some nodes die early. It also warns that the original LEACH gives a longer lifetime than HEED in LEACH's own scenario, "since HEED will produce only one cluster head for the entire network if we assume that every node can reach all other nodes in one hop (very large Rc)".

**The iteration rule (pseudocode from the paper, Fig. 2).**

```
I. Initialize
 1. S_nbr  <- {v : v lies within my cluster range}
 2. Compute and broadcast cost to S_nbr
 3. CH_prob <- max(C_prob * E_residual / E_max, p_min)
 4. is_final_CH <- FALSE
II. Repeat
 1. If ((S_CH <- {v : v is a cluster head}) != empty)
 2.     my_cluster_head <- least_cost(S_CH)
 3.     If (my_cluster_head = NodeID)
 4.         If (CH_prob = 1)
 5.             Cluster_head_msg(NodeID, final_CH, cost)
 6.             is_final_CH <- TRUE
 7.         Else
 8.             Cluster_head_msg(NodeID, tentative_CH, cost)
 9.     ElseIf (CH_prob = 1)
10.         Cluster_head_msg(NodeID, final_CH, cost)
11.         is_final_CH <- TRUE
12.     ElseIf Random(0,1) <= CH_prob
13.         Cluster_head_msg(NodeID, tentative_CH, cost)
14. CH_previous <- CH_prob
15. CH_prob <- min(CH_prob * 2, 1)
    Until CH_previous = 1
III. Finalize
 1. If (is_final_CH = FALSE)
 2.     If ((S_CH <- {v : v is a final cluster head}) != empty)
 3.         my_cluster_head <- least_cost(S_CH)
 4.         join_cluster(cluster_head_ID, NodeID)
 5.     Else Cluster_head_msg(NodeID, final_CH, cost)
 6. Else Cluster_head_msg(NodeID, final_CH, cost)
```

In words: each node starts with a probability proportional to its remaining energy, floored at p_min. It doubles that probability every iteration until it reaches 1, announcing itself as a tentative head when a random draw succeeds. A node that hears a head picks the least-cost one. A node still uncovered at the end declares itself a final head.

**Parameters set by the authors.** C_prob = 5% initially ("only used to limit the initial cluster head announcements"), p_min = 0.0005 in the simulations (10⁻⁴ as an example), cluster radius 25 m, data packet 100 bytes, 25-byte broadcast and header, one round = 5 TDM frames, 2 J per battery, Eelec = 50 nJ/bit, eps_fs = 10 pJ/bit/m², eps_mp = 0.0013 pJ/bit/m⁴, fusion 5 nJ/bit/signal, d_0 = 75 m, a grid from (0,0) to (100,100) with the sink at (50,175), and a node counts as dead once it has lost 99.9% of its energy.

**Left unstated or open for a reimplementation.** HEED needs several transmit power levels so nodes can compute AMRP, and the paper says nothing about how cluster heads reach the sink in a fixed simulator, other than single or multi-hop among cluster heads depending on the cluster range. Which cost type to use, the cluster radius for a small 40 m x 30 m field, p_min and the round length are all choices the study has to fix and record.

**How it bears on this study.** C_prob is the parameter the study tunes (over 0.02, 0.05, 0.1 and 0.2). In the study's simplified HEED, a node's election probability follows the rule above and the iteration count is bounded by the doubling. Its warning about very large cluster radius is relevant because the Intel field is small, so one cluster could cover most of it.

## Q4

**PEGASIS: Power-efficient gathering in sensor information systems** (Lindsey and Raghavendra, IEEE Aerospace Conference 2002). Read from a third-party hosted copy of the paper, since the IEEE original is paywalled.

**What it does.** It proposes a chain protocol that improves on LEACH: each node talks only to a close neighbour in a chain, data is fused as it moves along the chain, and one node per round sends to the base station. It compares direct transmission, LEACH and PEGASIS in C simulations of random 100-node networks.

**What it found.** "PEGASIS performs better than LEACH by about 100 to 300% when 1%, 20%, 50%, and 100% of nodes die for different network sizes and topologies." In its Table 1, for 0.25 J per node in the 50 m x 50 m field, the rounds at 1%, 20%, 50% and 100% of nodes dead are 402, 480, 523 and 635 for LEACH and 788, 1004, 1041 and 1096 for PEGASIS. It also gives an upper bound of about 1100 rounds before the first node dies (probably under 1000), and PEGASIS reaches about 800. The text claims about 3x for the 100 m x 100 m network, but the table gives about 2x at 1% dead, about 3x at 20% and 50%, and about 2.5x at 100% (0.25 J), and for the 50 m x 50 m network about 2x at 1% and 1.7x at 100%.

**How the chain is built (copied in substance from the paper).** The chain is built greedily before the first round, assuming every node knows all positions. "To construct the chain, we start with the furthest node from the BS." Then each step adds the nearest node not already on the chain, so neighbour distances grow gradually and nodes already on the chain cannot be revisited. When a node dies the chain is rebuilt in the same way to skip it.

**How data reaches the sink.** The leader in round i is node number i mod N, which puts it at a random position on the chain. The leader starts a small token that travels to both ends. Each node receives from one neighbour, fuses it with its own data into one packet of the same length, and passes it on. The leader receives from both sides, fuses, and sends one message to the base station.

**Parameters set by the authors.** 100 random nodes, a 50 m x 50 m field with the base station at (25, 150), and a 100 m x 100 m field with it at (50, 300), Eelec = 50 nJ/bit, amplifier 100 pJ/bit/m², packets of 2000 bits, fusion 5 nJ/bit/message, 0.25, 0.5 and 1 J per node.

**Left unstated.** The paper mentions "a threshold on neighbor distance" that stops nodes with distant chain neighbours from becoming leaders, but gives no value. It also does not say how ties between equally near nodes are resolved or how the 1% point is counted.

**Why it has no parameter to tune in this study.** The chain rule (greedy from the farthest node) and the leader rule (round mod N) are fixed by the paper, so there is nothing to sweep. The one adjustable thing, the leader-distance threshold, has no value in the paper, so the study leaves it out and records that choice, and PEGASIS shows `param_set = none` in every run.

**How it bears on this study.** It is the protocol with the shortest hops, so it is the main candidate to move up when link loss is added (H2). In its paper the base station is 100 m or more away, whereas ours is central, so the leader's hop to the sink is much shorter here.

## Q5

**Residual Energy-Based Cluster-Head Selection in WSNs for IoT Application (R-LEACH)** (Behera et al., IEEE Internet of Things Journal, 2019; read from the free arXiv copy 1902.01445).

**What it does.** It changes LEACH's threshold so that a node's chance of becoming a cluster head is scaled by its remaining energy and an optimal number of clusters. It compares R-LEACH with LEACH in MATLAB: 100 random nodes, 100 m x 100 m, base station at the centre, 4000-bit packets, 0.5 J per node.

**What it found.** The abstract reports a 60% gain in throughput, 66% in lifetime and 64% in residual energy over LEACH. The numbers this study reproduces (Section V.A, Fig. 6): "The first node for LEACH dies out at 1092 round whereas for R-LEACH it is at 1382 rounds. Similarly, the last node for LEACH dies out at 1510 rounds whereas for R-LEACH it is at 2474 rounds."

**How cluster heads are chosen.** In the first round, ordinary LEACH is used (Eq. 4: `T(n) = P / (1 - P*(r mod 1/P))` for n in G, else 0). In later rounds the modified threshold (Eq. 5) is

```
T(n) = [ P / (1 - P*(r mod 1/P)) ] * (E_residual / E_initial) * k_opt   for n in G
T(n) = 0                                                                  otherwise
```

and the optimal number of clusters (Eq. 6) is

```
k_opt = sqrt(n / (2*pi)) * sqrt( E_fs / (E_amp * d^4 * (2m - 1) * E_0 - m * E_DA) ) * M
```

where M is the network diameter, E_0 the initial energy and m the number of cluster heads in each cluster. Members pick a head by the strength of its announcement, as in LEACH, and heads send to the sink "in either single-hop or multi-hop".

**Table I (simulation parameters) as printed.** Network diameter 100 m², 100 nodes, total network energy E_0 = 0.5 J, "Energy dissipation: receiving (E_amp)" 0.0013 pJ/bit/m⁴, free-space E_fs 10 pJ/bit/m², "power amplifier (E_amp)" 100 pJ/bit/m², aggregation E_DA 5 nJ/bit.

**Left unstated or inconsistent.** I found no value for E_elec, for the cluster-head fraction P, or for the crossover distance in Table I or the text, and its labels are muddled (the 0.0013 pJ/bit/m⁴ entry is called "receiving", and a second E_amp of 100 pJ/bit/m² is carried over from LEACH). I found no number of repetitions or seeds either; the results read as a single run. In Eq. 5 the product with k_opt can push T(n) above 1, with no cap stated. Eq. 6 uses d⁴, which does not apply when all distances are below the crossover.

**How it bears on this study.** R-LEACH differs from LEACH only in the residual-energy factor, so the pair isolates that idea. The reproduction in the 100-node setting checks the rebuilt LEACH and R-LEACH against these four numbers by direction (R-LEACH later), not by exact values, because the published numbers come from a single layout. If R-LEACH does not beat LEACH there, the implementations get rechecked before the main grid. The parameter p for R-LEACH is tuned over the same grid as LEACH.

## Q6

**ECH: An Enhanced Clustering Hierarchy Approach to Maximize Lifetime of Wireless Sensor Networks** (El Alami and Najid, IEEE Access, vol. 7, 2019; open access).

**What it does.** Earlier clustering protocols ignore that sensors with overlapping sensing ranges collect redundant data. ECH adds a sleeping-waking mechanism on top of a LEACH-style cluster-head election, so that within each group of overlapping nodes only some nodes sense, aggregate and transmit in a given round. It also cuts communication distance: a normal node sends straight to the base station when the base station is closer than any cluster head. The authors apply it to LEACH, TEEN, SEP and DEEC (homogeneous and heterogeneous networks) and compare each against the original and against the (ACH)² variant, in MATLAB R2014b, with 100 immobile nodes, a base station at (50, 50), 0.5 J per node in the homogeneous case, and averages over 10 runs with a 90% confidence interval.

**What it found.** LEACH-ECH lengthens the stability period (first node dead) by 46.2% and the network lifetime by 36.56% compared with LEACH, and by 22.77% and 17.33% compared with LEACH-(ACH)². On the half-nodes-alive metric the ECH variants beat the originals by up to 41.02%. It also notes the ECH variants send fewer packets to the base station, because sleeping nodes send nothing.

**The sleep-wake rule (from Section III and Algorithm 1).**

1. Every node broadcasts an update packet (ID, received signal strength, position, base-station position, remaining energy). Each node n_i then forms its group of neighbouring nodes, the nodes whose sensing ranges overlap its own (Eq. 10):

   ```
   Q(i) = { n_j | d(n_i, n_j) <= 2*R_sense , i >= 1 }
   ```

   A node with no such neighbour is an **unpaired node**. Unpaired nodes stay awake every round until their energy is gone.
2. For each point Z of its sensing area, the total energy available for monitoring it is (Eq. 11): `E_t(Z) = sum of E(n_j) over nodes n_j that cover Z`.
3. Each node computes weights (Eq. 12 to 14):

   ```
   Weight1(n_i) = 1 / E_t(Z)
   Weight2(n_i) = R_sense / E(n_i)
   Weight3(n_i) = d(n_i, BS) / E(n_i)
   ```

   and sets a waiting time slot proportional to its weight, so a node with a smaller weight has a shorter wait and decides first.
4. While it waits, the node listens for WAKING notifications from neighbours. When its slot runs out, it checks whether its sensing range is already fully monitored by neighbours that announced they are awake. If it is, the node goes to sleep for this round. If it is not, the node broadcasts a WAKING notification and stays awake. Sleeping nodes switch off sensing, computation and radio. Every round the groups, weights and decisions are recomputed.

**Cluster heads and data flow.** Only waking and unpaired nodes take part in the election. Each draws a random number and compares it with a LEACH-style threshold Th. If Random <= Th, and the node has not been a cluster head in the last rounds, it becomes a candidate. The optimal number of clusters k_opt comes from the same first-order radio model (Eq. 15 to 23): `k_opt = sqrt( (n_w + n_up) * M / (2*pi*d_BS) ) = sqrt( 2*(n_w + n_up) / (2*pi*0.765) )`, and the target probability is `p_opt = k_opt / (n_w + n_up)` (Eq. 24). Its radio equations are the same as in Q2, but Eq. 17 prints the crossover distance as sqrt(eps_fs / eps_fs), an obvious typo for sqrt(eps_fs / eps_mp), and Eq. 18 charges the cluster-head-to-base-station hop with the free-space (d²) term. If there are too few candidates, normal nodes whose average distance to the candidates exceeds their distance to the base station join a re-election. If there are too many, candidates compare a fuzzy-logic "chance" built from their remaining energy and their summed distance to the other candidates, and the weakest go back to being normal nodes (Algorithm 2). Each normal node then sends directly to the base station if it hears the base station more strongly than any cluster head. Otherwise it joins the cluster head with the shortest distance, and cluster heads aggregate and send to the base station.

**Parameters set by the authors (Table 1).** Field "100 m²" (read as 100 m x 100 m), 100 nodes, base station at (50, 50), E_elec = 50 nJ/bit, eps_fs = 10 pJ/bit/m², eps_mp = 0.0013 pJ/bit/m⁴, E_DA = 5 nJ/bit/message, data size 3000 bytes, sensing range **R_sense = 10 m**.

**Left unstated or ambiguous.**
- Which weight, or what combination of Weight1 to 3, sets the waiting time in Algorithm 1. Line 2 of the algorithm only says the time slot is proportional to W(n_i), an element of the set of the three weights, and the text says "the current weights" without a formula for combining them.
- The threshold Th and the value of p for the cluster-head election, the constant in the time slot, and the fuzzy-logic rules of Algorithm 2.
- How "fully monitored" is tested in practice (it needs the geometry of overlapping disks, and the paper only supposes GPS-like localization).
- The field is written as "100 m²", the data size is 3000 bytes (the study uses 4000-bit packets), and no round length is given.

**How it bears on this study.** The parameter the study tunes is the overlap radius, over 2, 4, 6 and 8 m. In ECH the radius that sets who counts as a neighbour is 2·R_sense, with R_sense = 10 m in the paper, so a group radius of 20 m. The study's smaller values suit the 40 m x 30 m Intel box, but it must be written down exactly which quantity the "overlap radius" stands for (R_sense, so groups reach 2·R_sense, or the group distance itself) before coding, and this is worth checking with the mentor. ECH is also the protocol most likely to react to the real layout (H3), because its sleeping groups depend on how close motes actually are. Two cautions for the simulator: sleeping nodes send nothing, so "one packet per alive sensor per round" no longer holds for ECH and packets delivered must be read beside lifetime, and sleeping can stretch a run towards the 20,000-round cap.
