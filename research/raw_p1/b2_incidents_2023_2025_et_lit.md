# RAW P1 — matière brute (batch 2) — collecté 2026-10-15

## Euler Finance — mars 2023
- Chainalysis: "$197 Million Stolen: Euler Finance Flash Loan Attack Explained [UPDATED 4/6/23]" — hacker returned stolen funds, one of the largest DeFi recoveries. URL: https://www.chainalysis.com/blog/euler-finance-flash-loan-attack/
- Bloomberg (2023-03-13): "DeFi Lender Euler Finance Hit By $197 Million Hack, Experts Say" — attack drained $197M on Monday (13 mars 2023). URL: https://www.bloomberg.com/news/articles/2023-03-13/defi-s-euler-finance-hit-by-197-million-hack-experts-say
- Cyfrin: missing check on liquidity status; hack analysis. URL: https://www.cyfrin.io/blog/how-did-the-euler-finance-hack-happen-hack-analysis
- Hacken: hacker deposited 20M DAI → ~19.6M eDAI; donated 100M eDAI to reserve. URL: https://hacken.io/discover/euler-finance-hack/

## ezETH (Renzo) dépeg — avril 2024
- DLNews: "Renzo's ezETH falls as low as $700, leading to $56m in liquidations" — ezETH traded off peg Tuesday, ~$56M liquidations across DeFi protocols. URL: https://www.dlnews.com/articles/defi/renzos-ezeth-loses-ether-peg-drops-79-in-under-one-hour/
- Yahoo Finance: "Renzo Protocol's EZETH Faces Price Depeg Following End of Airdrop Campaign" — Renzo 2nd largest LRT, TVL > $3.3bn. URL: https://finance.yahoo.com/news/renzo-protocols-ezeth-faces-price-064841084.html
- Cryptoslate: depeg triggered liquidations across DeFi platforms. URL: https://cryptoslate.com/renzos-ezeth-token-depeg-triggers-liquidations-across-defi-platforms/
- Coinmonks observations: ezETH not fully recovered, ~2.3% discount at time of writing. URL: https://medium.com/coinmonks/observations-from-renzos-ezeth-depeg-c545dc217147
- CONTEXT: fin de la campagne de points/airdrop → retraits massifs + liquidité DEX fine → depeg. (à vérifier: date exacte avril 2024)

## USD0++ (Usual) dépeg — janvier 2025
- Blockworks: "Usual protocol's depeg spurs instability in DeFi markets" — trading ~$0.92; new exit option redeem USD0++ → USD0 at manually set floor. URL: https://blockworks.com/news/usual-depeg-spurs-defi-instability
- OneSafe: "The new mechanism imposed a floor price of $0.87 for USD0++ redemption, triggering panic. USD0++ slumped to $0.89 before partially recovering". URL: https://www.onesafe.io/blog/stablecoin-usd0-depegging-impact
- Rekt News: "hundreds of millions in USD0++ got trapped in protocols still dreaming of dollar valuations". URL: https://rekt.news/unusual-money
- Gate Learn: "Usual set the unconditional floor price for USD0++ to USD0 at 0.87, with the goal of triggering a liquidation of the ..." URL: https://www.gate.com/learn/articles/usual-explained-the-hidden-issues-behind-usd0-depegging-and-circular-loans-liquidation/6030
- MEDIUM (Jung-Hua Liu): roadmap published 2025-01-09 announcing floor 0.87 → depeg 2025-01-11. URL: https://medium.com/@gwrx2005/analysis-of-usd0-stablecoin-by-usual-money-48d131a98c8f
- KEY: signal PUBLIC ANTÉRIEUR (annonce du floor 0.87 le 9 janvier, avant le depeg du 11) — boucle de prêts circulaires (CDP) utilisant USD0++ comme collatéral à 1$.

## Cascade de liquidations du 10 octobre 2025
- FTI Consulting: "On October 10, 2025, more than $19 billion of crypto leverage was liquidated in roughly a day". URL: https://www.fticonsulting.com/insights/articles/crypto-crash-october-2025-leverage-met-liquidity
- CoinShares: "$19 billion liquidation wave followed Donald Trump's announcement of a 100% tariff on Chinese imports. The event was nine times larger than the February 2025 crash and 19 times greater than both the March 2020 meltdown and the FTX collapse of November 2022." URL: https://coinshares.com/us/insights/knowledge/billions-in-liquidations-what-happened/
- Forbes (2025-10-13): "Crypto's Black Friday: Inside The $19 Billion Market Meltdown". URL: https://www.forbes.com/sites/digital-assets/2025/10/13/cryptos-black-friday-inside-the-19-billion-market-meltdown/
- CoinDesk Data: "largest liquidation event in its history, with $19B in notional positions unwound within 24 hours". URL: https://data.coindesk.com/blogs/how-ccix-performed-during-cryptos-largest-liquidation-event

## Aave — bad debt CRV (nov. 2022)
- EigenPhi: "How AAVE's $1.6 Million Bad Debt Was Created" — whale dumped CRV market with 92M CRV borrowed from AAVE; short squeeze; Mango hacker (Eisenberg). URL: https://eigenphi.substack.com/p/how-aaves-16-million-bad-debt-was-333
- Blockworks: "Feature or Flaw? Aave Left With $1.7M in Bad Debt" (Aave dipped to ~$50). URL: https://blockworks.com/news/aave-curve-bad-debt
- Decrypt: "Aave Feeling the Squeeze Even After Failed Attempt by Mango Hacker". URL: https://decrypt.co/115596/aave-feeling-the-squeeze-even-after-failed-attempt-by-mango-hacker
- Aave governance forum: "Discussion: Reducing Long Tail Asset Risk" — CRV market not frozen → risk of significant bad debt. URL: https://governance.aave.com/t/discussion-reducing-long-tail-asset-risk/10748

## Stream Finance / xUSD — novembre 2025
- S&P Global Ratings: "On Nov. 3, 2025, Stream Finance reported a loss of around $93 million and froze redemptions of its stablecoin, xUSD"; title "Stream Finance's Collapse Highlights DeFi Contagion Risks". URL: https://www.spglobal.com/ratings/en/regulatory/article/digital-assets-brief-stream-finances-collapse-highlights-defi-contagion-risks-s101661035
- Yahoo Finance: "Stream Finance Loses $93 Million as Stablecoin XUSD Collapses" — external fund manager lost ~$93M of platform assets. URL: https://finance.yahoo.com/news/stream-finance-loses-93-million-225557903.html
- Pharos Watch case study: "The loss was real immediately but invisible on-chain for weeks, because the lending markets holding xUSD priced it at a fixed $1. On 4 November Stream disclosed ~$93M of losses, halted withdrawals; xUSD fell ~77% from $1 toward a 24h low near $0.26, freezing ~$160M of user deposits. Elixir's deUSD ~65% backed by loans to Stream, collapsed ~98% to ~$0.015 and was wound down; Stables Labs' USDX broke below $0.60 within days." URL: https://pharos.watch/learn/case-studies/stream-elixir-contagion-2025/
- CoinShares: "Stream Finance's $280M meltdown... Recursive leverage, flawed oracles, and missing risk controls". URL: https://coinshares.com/us/insights/the-node/edito-07-11-25/
- Zircuit: xUSD lost over 90%; spread across $285 million in interconnected DeFi debt. URL: https://www.zircuit.com/blog/behind-cryptos-biggest-collapses
- Legal500: Elixir shut down its stablecoin after Stream Finance's $93M collapse. URL: https://www.legal500.com/en/intelligence/united-states/finance-and-banking/elixir-shuts-down-its-stablecoin-after-stream-finance's-$93m-collapse
- CoinDesk (2025-11-04): https://www.coindesk.com/markets/2025/11/04/stream-finance-faces-usd93-million-loss-launches-legal-investigation

## Balancer — novembre 2025
- Check Point Research (2025-11-05): "How an Attacker Drained $128M from Balancer Through Rounding Error Exploitation" — Nov 3, 2025 07:46 UTC; $128.64M across six blockchain networks in under 30 minutes; rounding error in _upscaleArray + batchSwap. URL: https://research.checkpoint.com/2025/how-an-attacker-drained-128m-from-balancer-through-rounding-error-exploitation/
- Yahoo/CryptoNews (2025-11-06): exploit began Nov 3 at 07:46 UTC, "first detected by Hypernative's automated monitoring system". Whitehats recovered ~$750,000. URL: https://finance.yahoo.com/news/tiny-rounding-error-ignited-balancer-142052252.html
- Bloomberg (2025-11-03): >$100M drained. URL: https://www.bloomberg.com/news/articles/2025-11-03/hack-drains-over-100-million-from-crypto-protocol-balancer
- Trail of Bits (2025-11-07): analysis + guidance. URL: https://blog.trailofbits.com/2025/11/07/balancer-hack-analysis-and-guidance-for-the-defi-ecosystem/

## Littérature détection précoce
- "Stablecoin depegging risk prediction" — Pacific-Basin Finance Journal v90 (2025), S0927538X24003925 — predictive models with three machine learning approaches; four categories of risk factors from literature. URLs: https://www.sciencedirect.com/science/article/abs/pii/S0927538X24003925 ; https://ideas.repec.org/a/eee/pacfin/v90y2025ics0927538x24003925.html ; SSRN 4700764 https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4700764
- arXiv 2602.17842: "Machine Learning for Behavioral Wallet Detection in Stablecoin Anti-Money Laundering" — Ethereum dataset, empirical baseline for behavioral AML detection; ensemble learning. URL: https://arxiv.org/html/2602.17842v2
- arXiv 2608.20271: "Catching the Rug: Early Prediction of Fraudulent Memecoins on Solana via Machine Learning" — discusses prediction horizon < 5 min for earlier warning vs actionable lead time. URL: https://arxiv.org/html/2608.20271v1
- arXiv 2509.01168 (Yaremus et al. 2025): "Detecting rug pulls in decentralized exchanges: machine learning evidence from the TON blockchain". URL: https://arxiv.org/abs/2509.01168v1
- DMI-R (SSRN 5394133): "Decentralized Monetary Index-Risk (DMI-R), a composite indicator designed to function as an early warning system for central banks in a [crypto/decentralized monetary system]". URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5394133
- arXiv 2602.03874: "ASRI: An Aggregated Systemic Risk Index for Cryptocurrency Markets" — DeFi Liquidity Risk (25%): protocol concentration and leverage dynamics. URL: https://arxiv.org/html/2602.03874v1
- ScienceDirect S2096720926000588: "A Risk Scoring Framework for Critical Infrastructure of Decentralized [Finance]" — 558 exploit incidents analyzed; layered framework for DeFi vulnerability prioritization. URL: https://www.sciencedirect.com/science/article/pii/S2096720926000588
- WJARR-2025-2875: "Leveraging AI-powered data streams for predictive risk assessment in [DeFi]" — anomaly detection for early warning signals of flash loan attacks, liquidity drain risks, cascading failures. URL: https://wjarr.com/sites/default/files/fulltext_pdf/WJARR-2025-2875.pdf
- EEA (Enterprise Ethereum Alliance) "DeFi Risk Assessment Guidelines - Version 1". URL: https://entethalliance.org/specs/defi-risks/
- MDPI JRFM 18(1):38: "Risk Management in DeFi: Analyses of the Innovative Tools and [frameworks]". URL: https://www.mdpi.com/1911-8074/18/1/38

## Régulateurs
- FSB (2026-10): "Global stablecoin arrangements: Cross-border vulnerabilities and financial stability monitoring" — structure des GSC, propagation des vulnérabilités, "metrics that could support financial stability monitoring". URL: https://www.fsb.org/2026/10/global-stablecoin-arrangements-cross-border-vulnerabilities-and-financial-stability-monitoring/
- FSB press release 18/2025 (2025-10): "FSB finds significant gaps and inconsistencies in implementation of crypto and stablecoin recommendations" — peer review, état au août 2025; "regulation of global stablecoin arrangements is lagging"; "significant gaps and inconsistencies that could pose risks to financial stability". URL: https://www.fsb.org/2025/10/fsb-finds-significant-gaps-and-inconsistencies-in-implementation-of-crypto-and-stablecoin-recommendations/
- BIS AER 2025 ch. III: "The next-generation monetary and financial system" — risks of bank-issued stablecoins on public blockchains. URL: https://www.bis.org/publications/aer-2025/next-generation-monetary-financial-system
- Reuters (2025-06-24): "Central bank body BIS delivers stark stablecoin warning" — risks include monetary sovereignty, EM capital flight. URL: https://www.reuters.com/business/finance/central-bank-body-bis-delivers-stark-stablecoin-warning-2025-06-24/
- ESRB (2025-10): "Crypto-assets and decentralised finance" — "Financial stability risks are mounting in 2025 as crypto-assets, including stablecoins, go mainstream, buoyed by forceful US policy measures." URL: https://www.esrb.europa.eu/pub/pdf/reports/esrb.report202510_cryptoassets.en.pdf
- FSB: hub page crypto-assets & GSC. URL: https://www.fsb.org/work-of-the-fsb/financial-innovation-and-structural-change/crypto-assets-and-global-stablecoins/
- FSB (2022-02-16): "Assessment of Risks to Financial Stability from Crypto-assets" — stablecoin run, fire sales of reserve assets, liquidity mismatch; data gaps table with "Available Metrics". URL: https://www.consumerfinancialserviceslawmonitor.com/wp-content/uploads/sites/501/2022/02/Financial-Stability-Board-Feb.-16-2022_Assessment-of-Risks-to-Financial-Stability-from-Crypto-assets.pdf
