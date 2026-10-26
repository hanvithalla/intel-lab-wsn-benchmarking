# m200: Related-work notes on six field surveys

These notes become the first part of the related-work section. The study runs LEACH, HEED, PEGASIS, R-LEACH and ECH in one shared simulator on the Intel Berkeley Lab's real mote positions and measured link delivery probabilities. It separates the effect of real positions from the effect of measured link loss.

## Q1

**AI-Driven Energy-Efficient Routing in IoT-Based Wireless Sensor Networks: A Comprehensive Review** (Sensors 2025, 25(24), 7408)

**What it does.** A literature review of "over 100 studies" on energy-efficient routing for WSNs in the IoT, covering conventional and AI-enhanced methods: metaheuristics, machine learning, reinforcement learning and AI-based cross-layer routing. It sorts them into a classification, compares them on scalability, energy efficiency, throughput and packet delivery, and lists open problems.

**What it found.** Static routing falls short in dynamic environments, and AI-driven methods (metaheuristics, deep reinforcement learning, bio-inspired clustering) tackle scalability, reliability and energy limits. Its conclusion names persistent gaps in adaptive cluster management, multi-objective optimization, link-quality prediction and security, and says these need "rigorous real-world validation".

**How it bears on this study.** It makes the evaluation-gap complaint directly. In the introduction: "the lack of standardized datasets and evaluation benchmarks makes it difficult to compare AI-based routing frameworks objectively with traditional counterparts." In its open-problems section: "many proposed protocols are only evaluated through simulation or limited lab tests, failing to account for unpredictable challenges in real-world deployments", and it calls for "extensive field testing". The Intel Lab files are a public, downloadable measured deployment, so running the classic clustering protocols on that topology is a small, concrete step toward the standard benchmark the survey says is missing. It is not field testing, because the radios are still simulated. The survey also lists link-quality prediction as a gap, which fits the measured link probabilities used at the intel-measured level.

## Q2

**Energy-Efficient Routing Protocols in Wireless Sensor Networks a Comprehensive Survey and Future Directions** (Kumar V et al., ITM Web of Conferences 76, 03007, 2025)

**What it does.** A short conference paper that mixes a survey with a proposal. It reviews energy-efficient routing work (hierarchical, flat, location-based, and game-theory, machine-learning and metaheuristic approaches). It then proposes an AI-driven, security-aware, cross-layer routing framework, using deep learning for traffic prediction and reinforcement learning for path choice. It evaluates the framework in NS-3 and MATLAB with 100 nodes in a 500 m x 500 m area, a 50 m transmission range, 2 J per node and 512-byte packets, against LEACH, PEGASIS and HEED. It also says it validated the framework on a testbed of real sensor nodes.

**What it found.** Its stated problem is that "the majority of existing studies assume theoretical models/simulations, which do not consider real-world deployment scenarios", and that existing methods "typically lack validation with real-time data". Its conclusion is that the proposed framework beats the baselines. In its Table 2, network lifetime is 1200 rounds for LEACH, 1500 for PEGASIS, 1700 for HEED and 2500 for the proposed framework, and packet delivery ratio is 85%, 88%, 91% and 97%. It reports a 35% lifetime improvement.

**How it bears on this study.** Its diagnosis is the same as ours: simulation-only evaluation that ignores deployment constraints. Two details are useful for the related-work section. First, it also compares LEACH, PEGASIS and HEED, and its Table 2 ranks them HEED, then PEGASIS, then LEACH, on a random 100-node layout. That is the kind of ranking we test against a real topology. Second, it claims a real testbed but gives no testbed details (no node count, hardware, layout or measured link behaviour), and the Table 2 numbers come with no repetitions or spread. So it names the gap without closing it. Our study closes a small part of the gap with public measured data: real positions and measured per-pair delivery probabilities, 40 seeds per condition, and paired tests.

## Q3

**Computational intelligence techniques for energy efficient routing protocols in wireless sensor networks: A critique** (Sri Lakshmi et al., Transactions on Emerging Telecommunications Technologies, 2023)

*Source note: the full PDF is behind a paywall and could not be obtained. This note is based on the published abstract only, so the details below should be checked against the full paper if access becomes available.*

**What it does.** A critique based on a systematic literature review of energy-efficient routing for WSNs. It summarizes key challenges and proposed solutions and lists open research questions: integrating diverse topologies, cross-layer routing, multiple mobile sinks, QoS-aware routing for real-time applications, mathematical modelling for protocol evaluation, and "the challenges of testing routing protocols on real hardware".

**What it found.** Fault tolerance is vital for network resilience given limited resources and harsh environments. It suggests the RPL routing protocol with the node-based metric RNE for better energy efficiency, and points to hierarchical routing, "exemplified by the LEACH protocol and its variants", as a promising field.

**How it bears on this study.** Testing on real hardware is hard and costly, so most work stays in simulation. The Intel Lab measured topology is a partial answer. It brings real mote positions and real measured delivery probabilities into the simulator without building a testbed. It is only partial, because the delivery probabilities are averages over the 2004 deployment and the radios are modelled, not run. The critique also names LEACH-style hierarchical protocols as a promising area, which is the family this study tests.

## Q4

**Energy Efficient Routing in Wireless Sensor Networks: A Comprehensive Survey** (Nakas, Kandris and Visvardis, Algorithms 2020, 13(3), 72)

**What it does.** An analytical survey of classic and modern energy-efficient routing protocols. It classifies them into four categories: Communication Model, Network Structure, Topology, and Reliable Routing. Within each category the protocols are described, compared on specific performance metrics, and their advantages and disadvantages discussed.

**What it found.** Under Network Structure, flat protocols treat all nodes as equal and "perform well in networks with few sensor nodes, but they have extremely low scalability". Hierarchical protocols enable data aggregation, reduce communication overhead and give great scalability, so they suit large-scale networks with heavy load. It also warns that most research assumes homogeneous networks, which "may lead to unrealistic results because in real-life scenarios heterogeneous WSNs are too common to ignore". In the open issues it notes that congestion causes packet losses that "necessitate packet retransmissions that deplete the energy reserves of sensor nodes".

**Where the study's protocols sit.** Network Structure splits into Flat and Hierarchical. Hierarchical splits into Hierarchy based, Zone based and Fuzzy logic based. LEACH, HEED and PEGASIS are all described in Section 3.2.1, Hierarchy based, which has 59 examples. LEACH uses cluster heads that send directly to the base station, and the survey notes single-hop routing "is not suggested for sensor networks deployed in large areas". PEGASIS is described as an improvement of LEACH that builds chains, with one leader talking to the base station, and with higher energy efficiency than LEACH but delay for distant nodes. HEED elects cluster heads mostly on residual energy. ECH (2019) is not covered, but it is a clustering protocol and would belong to the same Hierarchy based group.

**How it bears on this study.** All four protocols we test belong to one structural family, so differences between them come from their cluster-head or chain rules and not from the family. The two warnings above, on unrealistic assumptions and on losses causing energy-costly retransmissions, match the link-loss step with up to 8 attempts per hop.

## Q5

**Variants of the Low-Energy Adaptive Clustering Hierarchy Protocol: Survey, Issues and Challenges** (Al-Shalabi, Anbar, Wan and Khasawneh, Electronics 2018, 7(8), 136)

**What it does.** A survey of clustering protocols derived from LEACH, claimed to be the first to focus on cluster formation and cluster-head (CH) selection. It proposes a taxonomy with two main categories, CH selection-based and cluster formation-based. Each has subcategories (residual energy, energy efficiency, distance, network coverage, routing path). It discusses 21 LEACH-based protocols, compares them on location, energy, complexity, reliability, multi-hop path and load balancing, and compares itself with existing surveys.

**What it found.** LEACH reduces power use by spreading the load across nodes, but "has many disadvantages in terms of CH selection, cluster formation, and energy efficiency". Its future issues are complexity, number of rounds, scalability, security and fault tolerance. On scalability it says LEACH suffers because of "direct communication from a CH to the BS", so cluster heads die early in large networks, and it recommends multi-hop protocols.

**Where R-LEACH fits.** R-LEACH appeared in 2019, after this survey, so it is not listed. Its rule multiplies the LEACH threshold by the node's residual energy over its initial energy. That makes it CH selection-based, in the residual-energy subcategory. The closest listed variant is I-LEACH, which "updates the threshold formula by introducing the remaining energy factor". The survey's point about LEACH ignoring residual energy is the exact weakness R-LEACH addresses.

**How it bears on this study.** It confirms that LEACH and R-LEACH differ in only one respect, the CH-selection threshold. That makes the LEACH versus R-LEACH comparison a clean test of the residual-energy idea, and it is why R-LEACH is the reproduction check (RQ4). Its remark about direct CH-to-BS hops supports hypothesis H1, that these protocols suffer most when long hops meet lossy links. The survey does not discuss real deployments or link loss at all.

## Q6

**Energy-Efficient Routing Protocols for Wireless Sensor Networks: Architectures, Strategies, and Performance** (Behera et al., Electronics 2022, 11(15), 2282)

**What it does.** A review of LEACH-based and bio-inspired clustering protocols, centred on how the cluster-head selection threshold has been modified. It describes each protocol with its pros, cons, assumptions and CH criteria, and compares longevity, scalability and packet delivery ratio. R-LEACH is covered in Section 3.2.14, with the threshold scaled by residual over initial energy and an optimal number of clusters.

**What it found.** Its conclusions are that LEACH-MAC suits networks where lifetime is the main issue, I-LEACH helps in both large and small networks (a 67% rise in throughput and a lifetime of 1750 rounds in its comparison), and LEACH-KH gives a high packet delivery ratio. It adds that LEACH's random CH choice means low-energy nodes can be picked, causing early network death.

**Simulation setting.** Its comparisons use 100 nodes deployed over 100 x 100 m², the base station at the centre (50, 50) in some figures and at (50, 175) in others, with the lifetime figures given for n = 100 and n = 400 and an initial energy of 0.5 J (the text for one comparison says 5 J). I found no use of measured positions or measured link loss.

**How it bears on this study.** This is the setting this study starts from and then moves away from: a uniform random layout in a large square, with a simple radio model. Our random-ideal level keeps the random positions and perfect links but shrinks them to match the Intel box (52 nodes in 0.5-40.5 m by 1-31 m, sink at (19.5, 19)). That way the first step changes only the geometry. The survey also supports the choice of metrics, since it reports lifetime and packet delivery ratio side by side, as we do with FND, HND, LND and PDR.
