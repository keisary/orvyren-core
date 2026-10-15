# https://arxiv.org/html/2606.07442v1

Title:

Content selection saved. Describe the issue below:

Description:

![](https://arxiv.org/static/base/1.0.1/images/icons/smileybones-small.svg)arXiv is now an independent nonprofit! [Learn more](https://info.arxiv.org/about) ×

[License: arXiv.org perpetual non-exclusive license](https://info.arxiv.org/help/license/index.html#licenses-available)

arXiv:2606.07442v1 \[cs.CE\] 05 Jun 2026

Graduate School of Advanced Integrated Studies in Human Survivability, Kyoto University, Japanhttps://orcid.org/0000-0002-7948-6220
Complexity Science Hub and AIT Austrian Institute of Technology, Austriahttps://orcid.org/0000-0001-8454-167X
Complexity Science Hub, Austriahttps://orcid.org/0000-0002-0415-4491
Graduate School of Advanced Integrated Studies in Human Survivability, Kyoto University, Graduate School of Data Science, Nagoya City University, Japanikeda.yuichi.2w@kyoto-u.ac.jp, ikeda@ds.nagoya-cu.ac.jphttps://orcid.org/0000-0002-9929-3813Ripple Impact Fund, Silicon Valley Community Foundation Grant 2022-247584 (5855)
{CCSXML}¡ccs2012¿
¡concept¿
¡concept\_id¿10010405.10010455.10010460¡/concept\_id¿
¡concept\_desc¿Applied computing Economics¡/concept\_desc¿
¡concept\_significance¿300¡/concept\_significance¿
¡/concept¿
¡/ccs2012¿

# Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse

Krongtum Sankaewtong
Stefan Kitzler
Bernhard Haslhofer
Yuichi Ikeda

###### Abstract

The March 2023 collapse of Silicon Valley Bank (SVB) disrupted the core premise of stablecoins, which are digital tokens designed to maintain a fixed value against the U.S. dollar and serve as on-chain substitutes for dollar liquidity. The event triggered a sharp depeg of USDC, creating a rare exogenous shock to the stablecoin ecosystem. While price deviations during this crisis are well documented, the underlying behavioral reorganization of on-chain activity remains less understood. Here, we analyze high-granularity transaction data to measure the shock’s effects on network activities, volumes, and prices, reconstructing the contagion pathway from market-wide synchronization down to account-level reallocation. By extracting phase dynamics, we first show that transaction activity across major stablecoins became strongly synchronized during the crisis window, indicating a collective market-level response. We then uncover a bifurcated contagion pathway. While USDT, WBTC, and WETH reacted primarily as liquidity absorption channels with larger trade volumes, only USDC-related assets exhibited immediate price responses alongside surging transaction counts. This reflects the dominant role of USDC-related assets in this incident and their immediate behavioral connection to user panic, driving a mass reallocation from single-coin to multi-coin portfolios. Finally, governed by persistent intraday time-zone rhythms and balance-size heterogeneity, these findings provide a comprehensive empirical framework for understanding systemic risk and flight-to-quality mechanisms in fractional-reserve digital asset networks.

###### ccs

Applied computing Economics

###### keywords

Blockchain, DeFi, Ethereum, Stablecoin, Financial Contagion, Transaction Networks, Phase Synchronization, Systemic Risk

††runningauthor: K. Sankaewtong, S. Kitzler, B. Haslhofer, and Y. Ikeda††copyright: Krongtum Sankaewtong, Stefan Kitzler, Bernhard Haslhofer, and Yuichi Ikeda††editors: John Q. Open and Joan R. Access††event-title: 42nd Conference on Very Important Topics (CVIT 2016)††event-shorttitle: CVIT 2016††event-acronym: CVIT††year: 2016††event-date: December 24–27, 2016††event-location: Little Whinging, United Kingdom††series-volume: 42††articleno: 23

## 1 Introduction

Stablecoins are digital assets designed to maintain a stable value relative to a reference asset, most commonly the U.S. dollar. By offering a low-volatility alternative to crypto-assets such as Bitcoin and Ether, they have become core instruments for liquidity provision, settlement, collateral management, and portfolio reallocation in digital-asset markets \[ [5](https://arxiv.org/html/2606.07442v1#bib.bib46 "")\], and are especially important in decentralized finance (DeFi), where they serve as on-chain substitutes for dollar liquidity in trading, lending, borrowing, and automated market-making protocols \[ [16](https://arxiv.org/html/2606.07442v1#bib.bib4 ""), [6](https://arxiv.org/html/2606.07442v1#bib.bib48 "")\]. This stability, however, depends on confidence in reserve quality, redemption mechanisms, issuer governance, and the banking infrastructure that supports off-chain reserves. Stablecoins are therefore designed to reduce volatility inside crypto markets, yet their pegs can become fragile when confidence in these supporting mechanisms is disrupted. Prior research shows that stablecoins differ substantially in collateral mechanisms, transparency, liquidity conditions, and resilience to market stress \[ [39](https://arxiv.org/html/2606.07442v1#bib.bib23 ""), [48](https://arxiv.org/html/2606.07442v1#bib.bib28 "")\]. During depegging events, stablecoins may act not only as safe-haven assets, but also as channels through which shocks propagate across digital-asset markets; understanding such instability therefore requires going beyond single-asset prices and examining how shocks reorganize transaction activity, network structure, and account behavior \[ [37](https://arxiv.org/html/2606.07442v1#bib.bib47 ""), [8](https://arxiv.org/html/2606.07442v1#bib.bib11 "")\].

The collapse of Silicon Valley Bank (SVB) in March 2023 exposed this fragility. Circle, the issuer of USDC, disclosed that approximately USD 3.3 billion, or nearly 8% of its cash reserves, was held at SVB, creating uncertainty about USDC’s redeemability \[ [16](https://arxiv.org/html/2606.07442v1#bib.bib4 "")\]. The disclosure triggered a sharp secondary-market depeg of USDC, affected related stablecoins such as DAI and FRAX through direct or indirect collateral links \[ [20](https://arxiv.org/html/2606.07442v1#bib.bib5 "")\], and coincided with reallocation toward alternative liquidity assets such as USDT and liquidity shifts across USDC-, USDT-, WETH-, and WBTC-related pools \[ [41](https://arxiv.org/html/2606.07442v1#bib.bib6 "")\].

Existing studies show that the SVB collapse affected financial markets, banking-sector indices, cryptocurrency prices, and DeFi liquidity \[ [2](https://arxiv.org/html/2606.07442v1#bib.bib7 ""), [55](https://arxiv.org/html/2606.07442v1#bib.bib8 ""), [30](https://arxiv.org/html/2606.07442v1#bib.bib9 ""), [3](https://arxiv.org/html/2606.07442v1#bib.bib10 "")\]. However, much of this work remains centered on price, volatility, abnormal returns, or aggregate market variables \[ [44](https://arxiv.org/html/2606.07442v1#bib.bib38 ""), [40](https://arxiv.org/html/2606.07442v1#bib.bib39 ""), [53](https://arxiv.org/html/2606.07442v1#bib.bib40 ""), [54](https://arxiv.org/html/2606.07442v1#bib.bib14 "")\]. Less is known about the on-chain behavioral pathway through which the shock propagated across transaction activity, asset flows, and account behavior.

This paper addresses that gap by reconstructing the multiscale on-chain response to the SVB-induced USDC depeg. Using high-granularity Ethereum ERC-20 transfer data for USDC, DAI, FRAX, USDP, USDT, BUSD, WETH, and WBTC, we construct directed transaction graphs and combine phase synchronization analysis, autoregressive distributed lag (ARDL) models, account-state transitions, intraday activity profiles, and wealth-group segmentation. This follows prior on-chain network studies showing that transaction graphs and account movements can reveal crisis dynamics beyond price series alone \[ [8](https://arxiv.org/html/2606.07442v1#bib.bib11 ""), [56](https://arxiv.org/html/2606.07442v1#bib.bib12 "")\].

Our central research question is: _How did stablecoin users reorganize across scales during the SVB-induced depeg event?_ We make four contributions. First, we quantify market-level synchronization in transaction activity across major stablecoin-related assets, showing that transaction-count activity became more phase-aligned during the depeg window.
Second, we distinguish two asset-level propagation channels: USDC-related stablecoins transmitted the shock through broad transaction-count and active-node participation, whereas USDT, WBTC, and WETH responded mainly through larger value transfers.
Third, we reconstruct account-level reallocation and show a shift from single-asset toward multi-asset exposure, including a short-lag price-linked movement from USDC toward USDT, consistent with USDT acting as an alternative liquidity destination during the crisis.
Finally, we show that the depeg partially overwhelmed normal intraday market-hour rhythms and that lower- and medium-wealth accounts adjusted more strongly in relative terms than high-wealth accounts.

Together, these findings show that the SVB-induced USDC depeg was not only a price event, but a contagion process unfolding across several token-layers. The proposed analytical framework could therefore inform the design of stablecoin systemic-risk monitoring mechanisms that combine peg deviations with activity synchronization, transaction-network responses, and user-flow indicators.

## 2 Background and Related Work

### 2.1 Stablecoin Landscape and Peg-Stability Mechanisms

Stablecoins are digital assets designed to maintain a stable value relative to a reference asset, most commonly the U.S. dollar. By combining fiat’s unit of account with the programmability, continuous availability, and borderless settlement of public blockchains, they have become central to crypto trading, on-chain payments, and DeFi collateral. Their growing importance is reflected in market capitalization above USD 255 billion, sizeable issuer purchases of short-dated U.S. Treasuries, corporate interest in private stablecoin issuance \[ [4](https://arxiv.org/html/2606.07442v1#bib.bib42 ""), [17](https://arxiv.org/html/2606.07442v1#bib.bib44 "")\], and emerging EU and U.S. regulatory frameworks \[ [23](https://arxiv.org/html/2606.07442v1#bib.bib43 ""), [50](https://arxiv.org/html/2606.07442v1#bib.bib45 "")\].


[... middle omitted — see footer ...]


- \[51\]D. Vidal-Tomás, A. Briola, and T. Aste (2023)FTX’s downfall and binance’s consolidation: the fragility of centralised digital finance.
Physica A: Statistical Mechanics and its Applications625, pp. 129044.
External Links: ISSN 0378-4371,
[Document](https://dx.doi.org/10.1016/j.physa.2023.129044 ""),
[Link](https://www.sciencedirect.com/science/article/pii/S037843712300599X "")Cited by: [§2.2](https://arxiv.org/html/2606.07442v1#S2.SS2.p1.1 "2.2 Prior Literature on Stablecoin Depegs and Contagion ‣ 2 Background and Related Work ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse").

- \[52\]I. Vynyavskyy, S. Kitzler, B. Haslhofer, and A. Yaish (2026)Modern portfolio theory in the crypto-wilderness.
External Links: 2605.20528,
[Link](https://arxiv.org/abs/2605.20528 "")Cited by: [item Token holdings.](https://arxiv.org/html/2606.07442v1#S3.I1.ix3.p1.1 "In 3.1 Data and Event Window ‣ 3 Methods ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse").

- \[53\]M. P. Yadav, A. Rao, M. Z. Abedin, S. Tabassum, and B. Lucey (2023)The domino effect: analyzing the impact of silicon valley bank’s fall on top equity indices around the world.
Finance Research Letters55, pp. 103952.
External Links: ISSN 1544-6123,
[Document](https://dx.doi.org/https%3A//doi.org/10.1016/j.frl.2023.103952 "")Cited by: [§1](https://arxiv.org/html/2606.07442v1#S1.p3.1 "1 Introduction ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse").

- \[54\]I. Yousaf and J. W. Goodell (2023)Responses of us equity market sectors to the silicon valley bank implosion.
Finance Research Letters55, pp. 103934.
External Links: ISSN 1544-6123,
[Document](https://dx.doi.org/https%3A//doi.org/10.1016/j.frl.2023.103934 "")Cited by: [§1](https://arxiv.org/html/2606.07442v1#S1.p3.1 "1 Introduction ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse"),
[§2.2](https://arxiv.org/html/2606.07442v1#S2.SS2.p1.1 "2.2 Prior Literature on Stablecoin Depegs and Contagion ‣ 2 Background and Related Work ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse"),
[§3.1](https://arxiv.org/html/2606.07442v1#S3.SS1.p5.1 "3.1 Data and Event Window ‣ 3 Methods ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse").

- \[55\]I. Yousaf, Y. Riaz, and J. W. Goodell (2023)The impact of the svb collapse on global financial markets: substantial but narrow.
Finance Research Letters55, pp. 103948.
External Links: ISSN 1544-6123,
[Document](https://dx.doi.org/https%3A//doi.org/10.1016/j.frl.2023.103948 "")Cited by: [§1](https://arxiv.org/html/2606.07442v1#S1.p3.1 "1 Introduction ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse"),
[§2.2](https://arxiv.org/html/2606.07442v1#S2.SS2.p1.1 "2.2 Prior Literature on Stablecoin Depegs and Contagion ‣ 2 Background and Related Work ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse").

- \[56\]J. Zhu, A. Khan, and C. G. Akcora (2024)Data depth and core-based trend detection on blockchain transaction networks.
Frontiers in Blockchain7.
External Links: [Document](https://dx.doi.org/10.3389/fbloc.2024.1342956 ""),
ISSN 2624-7852Cited by: [§1](https://arxiv.org/html/2606.07442v1#S1.p4.1 "1 Introduction ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse"),
[§2.2](https://arxiv.org/html/2606.07442v1#S2.SS2.p2.1 "2.2 Prior Literature on Stablecoin Depegs and Contagion ‣ 2 Background and Related Work ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse"),
[§5](https://arxiv.org/html/2606.07442v1#S5.p1.1 "5 Discussion ‣ Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse").

──────── [TRUNCATED] ────────
Showing 10,192 chars (head) + 3,924 chars (tail) of 110,901 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\arxiv.org-5ea19b378a.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\arxiv.org-5ea19b378a.md" offset=69 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────