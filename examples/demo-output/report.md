# TraceX Investigation Report

> Generated 2026-11-19T03:46:58Z · chain **BTC** · TraceX v1.0.0  
> ⚠️ Heuristic analysis of public ledger data. Findings are investigative leads, **not proof** of identity or wrongdoing.

## 1. Summary

| Metric | Value |
|---|---|
| Seeds | `bc1q_demo_ransom_1` |
| Addresses | 35 |
| Transactions | 17 |
| Edges | 55 |
| Labeled addresses | 11 |
| Clusters | 1 |
| CoinJoins | 1 |
| Peel chains | 1 |
| Total volume (BTC) | 34.175500 |
| Fees (BTC) | 0.009500 |
| Period | 2026-01-01 00:00:00 UTC → 2026-01-06 10:11:59 UTC |
| Tainted addresses | 25 |

## 2. Risk assessment

### 🔴 `bc1q_demo_ransom_1` — **100/100 (severe)**

| Risk factor | Detail | Contribution |
|---|---|---|
| Ransomware exposure | DemoLocker ransom wallet #1 (target) | 0.95 |
| Taint | 100.0% of received value traces to illicit sources | 0.90 |
| Darknet market exposure | DemoMarket escrow (4 hop(s)) | 0.26 |
| Layering | peel chain within 2 hops | 0.15 |
| Layering | rapid pass-through within 2 hops | 0.10 |
| Gambling exposure | DemoCasino (5 hop(s)) | 0.04 |
| Exchange (KYC) exposure | DemoExchange deposit (3 hop(s)) | 0.03 |

## 3. Findings

| Severity | Type | Finding | Detail |
|---|---|---|---|
| 🔴 critical | labeled_entity | Ransomware: DemoLocker ransom wallet #1 | Address bc1q_demo_ransom_1 is labeled 'DemoLocker ransom wallet #1' (ransomware, confidence 100%, source: TraceX synthetic demo) and appears in the traced flow. |
| 🔴 critical | labeled_entity | Ransomware: DemoLocker ransom wallet #2 | Address bc1q_demo_ransom_2 is labeled 'DemoLocker ransom wallet #2' (ransomware, confidence 100%, source: TraceX synthetic demo) and appears in the traced flow. |
| 🔴 critical | labeled_entity | Sanctioned entity: Synthetic sanctioned entity | Address bc1q_demo_sanctioned is labeled 'Synthetic sanctioned entity' (sanctioned, confidence 100%, source: TraceX synthetic demo) and appears in the traced flow. |
| 🟠 high | labeled_entity | Darknet market: DemoMarket escrow | Address bc1q_demo_market_1 is labeled 'DemoMarket escrow' (darknet_market, confidence 100%, source: TraceX synthetic demo) and appears in the traced flow. |
| 🟠 high | labeled_entity | Darknet market: DemoMarket hot wallet | Address bc1q_demo_market_hot is labeled 'DemoMarket hot wallet' (darknet_market, confidence 90%, source: TraceX synthetic demo) and appears in the traced flow. |
| 🟡 medium | coinjoin | CoinJoin / mixing transaction | 5 equal outputs of 2 BTC (5 inputs -> 6 outputs). Output links to inputs are deliberately ambiguous; downstream attribution confidence is reduced. |
| 🟡 medium | peel_chain | Peel chain of 4 hops | Large balance repeatedly split into a small 'peel' payment and a large change output; 0.96 BTC peeled in total. Peel endpoints: no labeled endpoints. |
| 🟡 medium | pass_through | 3 rapid pass-through address(es) | Addresses that forwarded >=90% of received funds within 60 minutes - typical of layering / relay wallets. |
| ℹ️ info | cluster | Address cluster #1 (2 addresses) | Addresses spent together as inputs of one transaction (common-input-ownership). Cluster inherits label: DemoLocker ransom wallet #1 [ransomware]. |

## 4. Money-flow diagram

```mermaid
flowchart LR
  n0(("DemoLocker ransom wallet  1<br/>2.5 BTC in<br/>taint 100%")):::ransomware
  n1["Victim C<br/>0 BTC in"]:::victim
  n2["ShadyEx  no-KYC<br/>1.999 BTC in<br/>taint 20%"]:::exchange_nokyc
  n3["Victim B<br/>0 BTC in"]:::victim
  n4["DemoMarket hot wallet<br/>0.5475 BTC in<br/>taint 100%"]:::darknet_market
  n5["Victim A<br/>0 BTC in"]:::victim
  n6["DemoMarket escrow<br/>0.2495 BTC in<br/>taint 100%"]:::darknet_market
  n7["DemoLocker ransom wallet  2<br/>0 BTC in<br/>taint 100%"]:::ransomware
  n8["DemoExchange deposit<br/>0.409 BTC in<br/>taint 100%"]:::exchange_kyc
  n9["Synthetic sanctioned entity<br/>0.3 BTC in<br/>taint 100%"]:::sanctioned
  n10["DemoCasino<br/>0.2995 BTC in<br/>taint 100%"]:::gambling
  n11["bc1q_demo_collect<br/>2.999 BTC in<br/>taint 100%"]:::unlabeled
  n12["bc1q_demo_chg_1<br/>2.799 BTC in<br/>taint 100%"]:::unlabeled
  n13["bc1q_demo_chg_2<br/>2.548 BTC in<br/>taint 100%"]:::unlabeled
  n14["bc1q_demo_chg_3<br/>2.248 BTC in<br/>taint 100%"]:::unlabeled
  n15["bc1q_demo_chg_4<br/>2.037 BTC in<br/>taint 100%"]:::unlabeled
  n16["bc1q_demo_cj_out_1<br/>2 BTC in<br/>taint 20%"]:::unlabeled
  n17["bc1q_demo_hop_1<br/>2 BTC in<br/>taint 20%"]:::unlabeled
  n18["bc1q_demo_user_1<br/>0 BTC in"]:::unlabeled
  n19["bc1q_demo_cj_out_4<br/>2 BTC in<br/>taint 20%"]:::unlabeled
  n20["bc1q_demo_user_2<br/>0 BTC in"]:::unlabeled
  n21["bc1q_demo_cj_out_3<br/>2 BTC in<br/>taint 20%"]:::unlabeled
  n22["bc1q_demo_user_3<br/>0 BTC in"]:::unlabeled
  n23["bc1q_demo_cj_out_2<br/>2 BTC in<br/>taint 20%"]:::unlabeled
  n24["bc1q_demo_user_4<br/>0 BTC in"]:::unlabeled
  n25["bc1q_demo_cj_out_5<br/>2 BTC in<br/>taint 20%"]:::unlabeled
  n26["bc1q_demo_victim_3c<br/>0.7995 BTC in"]:::unlabeled
  n27["bc1q_demo_victim_2c<br/>0.6995 BTC in"]:::unlabeled
  n28["bc1q_demo_peel_3<br/>0.3 BTC in<br/>taint 100%"]:::unlabeled
  n29["bc1q_demo_peel_2<br/>0.25 BTC in<br/>taint 100%"]:::unlabeled
  n30["bc1q_demo_victim_1c<br/>0.4995 BTC in"]:::unlabeled
  n31["bc1q_demo_peel_4<br/>0.21 BTC in<br/>taint 100%"]:::unlabeled
  n32["bc1q_demo_peel_1<br/>0.2 BTC in<br/>taint 100%"]:::unlabeled
  n33["bc1q_dem…_hot_c<br/>0.2465 BTC in<br/>taint 100%"]:::unlabeled
  n34["bc1q_demo_cj_chg<br/>0.0365 BTC in<br/>taint 20%"]:::unlabeled
  n0 -->|2.499 BTC| n11
  n7 -->|0.4998 BTC| n11
  n5 -->|0.5 BTC| n0
  n5 -->|0.4995 BTC| n30
  n3 -->|0.8 BTC| n0
  n3 -->|0.6995 BTC| n27
  n1 -->|1.2 BTC| n0
  n1 -->|0.7995 BTC| n26
  n11 -->|0.2 BTC| n32
  n11 -->|2.799 BTC| n12
  n32 -->|0.1995 BTC| n8
  n12 -->|0.25 BTC| n29
  n12 -->|2.548 BTC| n13
  n29 -->|0.2495 BTC| n6
  n13 -->|0.3 BTC| n28
  n13 -->|2.248 BTC| n14
  n6 -->|0.5475 BTC| n4
  n28 -->|0.2995 BTC| n10
  n14 -->|0.21 BTC| n31
  n14 -->|2.037 BTC| n15
  n4 -->|0.3 BTC| n9
  n4 -->|0.2465 BTC| n33
  n31 -->|0.2095 BTC| n8
  n15 -->|0.4059 BTC| n16
  n15 -->|0.4059 BTC| n23
  n15 -->|0.4059 BTC| n21
  n15 -->|0.4059 BTC| n19
  n15 -->|0.4059 BTC| n25
  n15 -->|0.007408 BTC| n34
  n18 -->|0.3985 BTC| n16
  n18 -->|0.3985 BTC| n23
  n18 -->|0.3985 BTC| n21
  n18 -->|0.3985 BTC| n19
  n18 -->|0.3985 BTC| n25
  n18 -->|0.007273 BTC| n34
  n20 -->|0.3985 BTC| n16
  n20 -->|0.3985 BTC| n23
  n20 -->|0.3985 BTC| n21
  n20 -->|0.3985 BTC| n19
  n20 -->|0.3985 BTC| n25
  n20 -->|0.007273 BTC| n34
  n22 -->|0.3985 BTC| n16
  n22 -->|0.3985 BTC| n23
  n22 -->|0.3985 BTC| n21
  n22 -->|0.3985 BTC| n19
  n22 -->|0.3985 BTC| n25
  n22 -->|0.007273 BTC| n34
  n24 -->|0.3985 BTC| n16
  n24 -->|0.3985 BTC| n23
  n24 -->|0.3985 BTC| n21
  n24 -->|0.3985 BTC| n19
  n24 -->|0.3985 BTC| n25
  n24 -->|0.007273 BTC| n34
  n16 -->|2 BTC| n17
  n17 -->|1.999 BTC| n2
  classDef sanctioned fill:#b91c1c33,stroke:#b91c1c,stroke-width:2px,color:#111;
  classDef ransomware fill:#dc262633,stroke:#dc2626,stroke-width:2px,color:#111;
  classDef theft fill:#ea580c33,stroke:#ea580c,stroke-width:2px,color:#111;
  classDef darknet_market fill:#9333ea33,stroke:#9333ea,stroke-width:2px,color:#111;
  classDef scam fill:#c026d333,stroke:#c026d3,stroke-width:2px,color:#111;
  classDef mixer fill:#f59e0b33,stroke:#f59e0b,stroke-width:2px,color:#111;
  classDef exchange_nokyc fill:#ca8a0433,stroke:#ca8a04,stroke-width:2px,color:#111;
  classDef gambling fill:#0284c733,stroke:#0284c7,stroke-width:2px,color:#111;
  classDef defi fill:#0d948833,stroke:#0d9488,stroke-width:2px,color:#111;
  classDef exchange_kyc fill:#16a34a33,stroke:#16a34a,stroke-width:2px,color:#111;
  classDef service fill:#64748b33,stroke:#64748b,stroke-width:2px,color:#111;
  classDef victim fill:#2563eb33,stroke:#2563eb,stroke-width:2px,color:#111;
  classDef unlabeled fill:#94a3b833,stroke:#94a3b8,stroke-width:2px,color:#111;
```

## 5. Category flow (Sankey, by hop)

```mermaid
sankey-beta

Unlabeled h5,Unlabeled h6,10.036500
Ransomware h0,Unlabeled h1,2.999000
Unlabeled h1,Unlabeled h2,2.998500
Unlabeled h2,Unlabeled h3,2.798000
Unlabeled h3,Unlabeled h4,2.547500
Victim h-1,Ransomware h0,2.500000
Unlabeled h4,Unlabeled h5,2.247000
Unlabeled h6,Unlabeled h7,1.999500
Unlabeled h7,Exchange  no/weak KYC  h8,1.999000
Darknet market h4,Darknet market h5,0.547500
Darknet market h5,Sanctioned entity h6,0.300000
Unlabeled h4,Gambling h5,0.299500
Unlabeled h3,Darknet market h4,0.249500
Darknet market h5,Unlabeled h6,0.246500
Unlabeled h2,Exchange  KYC  h3,0.199500
```

## 6. Chronological sequence

```mermaid
sequenceDiagram
  autonumber
  participant A0 as DemoLocker ransom wallet  1
  participant A1 as Victim C
  participant A2 as ShadyEx  no-KYC
  participant A3 as Victim B
  participant A4 as DemoMarket hot wallet
  participant A5 as Victim A
  participant A6 as DemoMarket escrow
  participant A7 as DemoLocker ransom wallet  2
  participant A8 as DemoExchange deposit
  A5->>A0: 0.5 BTC (2026-01-01)
  A3->>A0: 0.8 BTC (2026-01-01)
  A1->>A0: 1.2 BTC (2026-01-01)
  A6->>A4: 0.5475 BTC (2026-01-05)
```

## 7.1 Peel chain (4 hops)

```mermaid
flowchart LR
  T0["tx 773b5ae9<br/>2.999 BTC"]
  P0(["bc1q_demo_peel_1<br/>peel"]):::unlabeled
  T0 -->|peel| P0
  T0 ==>|change| T1
  T1["tx a384df64<br/>2.799 BTC"]
  P1(["bc1q_demo_peel_2<br/>peel"]):::unlabeled
  T1 -->|peel| P1
  T1 ==>|change| T2
  T2["tx 41806e1b<br/>2.548 BTC"]
  P2(["bc1q_demo_peel_3<br/>peel"]):::unlabeled
  T2 -->|peel| P2
  T2 ==>|change| T3
  T3["tx f2abaccd<br/>2.248 BTC"]
  P3(["bc1q_demo_peel_4<br/>peel"]):::unlabeled
  T3 -->|peel| P3
  classDef sanctioned fill:#b91c1c33,stroke:#b91c1c;
  classDef ransomware fill:#dc262633,stroke:#dc2626;
  classDef theft fill:#ea580c33,stroke:#ea580c;
  classDef darknet_market fill:#9333ea33,stroke:#9333ea;
  classDef scam fill:#c026d333,stroke:#c026d3;
  classDef mixer fill:#f59e0b33,stroke:#f59e0b;
  classDef exchange_nokyc fill:#ca8a0433,stroke:#ca8a04;
  classDef gambling fill:#0284c733,stroke:#0284c7;
  classDef defi fill:#0d948833,stroke:#0d9488;
  classDef exchange_kyc fill:#16a34a33,stroke:#16a34a;
  classDef service fill:#64748b33,stroke:#64748b;
  classDef victim fill:#2563eb33,stroke:#2563eb;
  classDef unlabeled fill:#94a3b833,stroke:#94a3b8;
```

## 8. Address clusters

```mermaid
flowchart TB
  subgraph C1["Cluster 1: DemoLocker ransom wallet  1"]
    C1_0["DemoLocker ransom wallet  1"]:::ransomware
    C1_1["DemoLocker ransom wallet  2"]:::ransomware
  end
  classDef sanctioned fill:#b91c1c33,stroke:#b91c1c;
  classDef ransomware fill:#dc262633,stroke:#dc2626;
  classDef theft fill:#ea580c33,stroke:#ea580c;
  classDef darknet_market fill:#9333ea33,stroke:#9333ea;
  classDef scam fill:#c026d333,stroke:#c026d3;
  classDef mixer fill:#f59e0b33,stroke:#f59e0b;
  classDef exchange_nokyc fill:#ca8a0433,stroke:#ca8a04;
  classDef gambling fill:#0284c733,stroke:#0284c7;
  classDef defi fill:#0d948833,stroke:#0d9488;
  classDef exchange_kyc fill:#16a34a33,stroke:#16a34a;
  classDef service fill:#64748b33,stroke:#64748b;
  classDef victim fill:#2563eb33,stroke:#2563eb;
  classDef unlabeled fill:#94a3b833,stroke:#94a3b8;
```

## 9. Labeled entities in scope

| Address | Entity | Category | Confidence | Source | Taint |
|---|---|---|---|---|---|
| `bc1q_demo_ransom_1` | DemoLocker ransom wallet #1 | Ransomware | 100% | TraceX synthetic demo | 100% |
| `bc1q_demo_ransom_2` | DemoLocker ransom wallet #2 | Ransomware | 100% | TraceX synthetic demo | 100% |
| `bc1q_demo_victim_1` | Victim A | Victim | 100% | TraceX synthetic demo | 0% |
| `bc1q_demo_victim_2` | Victim B | Victim | 100% | TraceX synthetic demo | 0% |
| `bc1q_demo_victim_3` | Victim C | Victim | 100% | TraceX synthetic demo | 0% |
| `bc1q_demo_exch_kyc` | DemoExchange deposit | Exchange (KYC) | 100% | TraceX synthetic demo | 100% |
| `bc1q_demo_market_1` | DemoMarket escrow | Darknet market | 100% | TraceX synthetic demo | 100% |
| `bc1q_demo_market_hot` | DemoMarket hot wallet | Darknet market | 90% | TraceX synthetic demo | 100% |
| `bc1q_demo_casino` | DemoCasino | Gambling | 100% | TraceX synthetic demo | 100% |
| `bc1q_demo_sanctioned` | Synthetic sanctioned entity | Sanctioned entity | 100% | TraceX synthetic demo | 100% |
| `bc1q_demo_exch_nokyc` | ShadyEx (no-KYC) | Exchange (no/weak KYC) | 80% | TraceX synthetic demo | 20% |

## 10. Largest transactions

| Time | Txid | In→Out | Total (BTC) | Flags |
|---|---|---|---|---|
| 2026-01-06 00:00:00 UTC | `c1126c99ec2dea0e…` | 5→6 | 10.036500 | coinjoin |
| 2026-01-02 06:00:00 UTC | `c003873192476dcd…` | 2→1 | 2.999000 |  |
| 2026-01-02 16:00:00 UTC | `773b5ae95eccba98…` | 1→2 | 2.998500 | peel |
| 2026-01-03 04:00:00 UTC | `a384df647ae273a1…` | 1→2 | 2.798000 | peel |
| 2026-01-03 22:00:00 UTC | `41806e1b303b5199…` | 1→2 | 2.547500 | peel |
| 2026-01-04 18:00:00 UTC | `f2abaccd87228073…` | 1→2 | 2.247000 | peel |
| 2026-01-01 09:00:00 UTC | `ba961be77dfcd8c2…` | 1→2 | 1.999500 |  |
| 2026-01-06 10:00:00 UTC | `2f828a82c8e864a4…` | 1→1 | 1.999500 |  |
| 2026-01-06 10:11:59 UTC | `8c8d1312fd5a777c…` | 1→1 | 1.999000 |  |
| 2026-01-01 05:00:00 UTC | `56969e35981f5ef8…` | 1→2 | 1.499500 |  |
| 2026-01-01 00:00:00 UTC | `e8c54b0c900e9df5…` | 1→2 | 0.999500 |  |
| 2026-01-05 04:00:00 UTC | `b61d7e76f2e6c754…` | 1→1 | 0.547500 |  |
| 2026-01-05 14:00:00 UTC | `0bfeb2f3d8d0c750…` | 1→2 | 0.546500 |  |
| 2026-01-04 00:00:00 UTC | `5f063cb75516f075…` | 1→1 | 0.299500 |  |
| 2026-01-03 06:00:00 UTC | `c9fd3ea2791971b7…` | 1→1 | 0.249500 |  |

## 11. Methodology & limitations

- Attribution comes **only** from the label files you supplied; unlabeled ≠ innocent.
- Common-input clustering is excluded for CoinJoins but can still over-merge (e.g., PayJoin).
- Change detection, peel chains and taint are probabilistic. Haircut taint is proportional; poison taint is worst-case.
- Traces are bounded by depth / transaction caps; see `manifest.json` for exact parameters.
- Do not treat output as legal evidence without independent corroboration and chain-of-custody review.
