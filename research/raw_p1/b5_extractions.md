# RAW P1 — matière brute (batch 5, extractions) — collecté 2026-10-15

## Fed FEDS Note (2025-12-17) — Du, Sonawane, Watsky, "In the Shadow of Bank Runs: Lessons from the Silicon Valley Bank Failure and Its Impact on Stablecoins"
URL: https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html
DOI: 10.17016/2380-7172.3958
Verbatim utiles :
- "Stablecoins perform dollar-like functions in decentralized finance ('DeFi') and represent a run-able liability for their issuers. As with money market funds and bank deposits, stablecoins are susceptible to crises of confidence, contagion, and self-reinforcing runs."
- "Shortly after, Circle, the issuer of USDC, publicly announced that it was unable to access a portion of its dollar reserves held as (uninsured) deposits at SVB. This announcement precipitated a surge in redemption requests by holders of USDC, causing the stablecoin to lose its peg against the dollar on secondary markets when Circle shut down primary market operations over the weekend."
- "At the same time during the resolution of SVB, a crypto-collateralized stablecoin, Dai, was operating one-to-one exchange facilities — called Peg Stability Modules ('PSMs') — against USDC and other stablecoins. Over the weekend, these PSMs were rapidly drained of liquidity. Dai, and other stablecoins with otherwise no exposure to SVB, also lost their peg to the dollar."
- "Both the SVB run and the stablecoins depegs were ameliorated when the FDIC, the Treasury Department, and the Federal Reserve Board jointly announced that all depositors in SVB would be fully protected."
- "First, there is a potential for two-way feedback between the traditional and the DeFi sectors."
- "Third, smart contracts, such as the one-to-one exchange facilities backing Dai, can create interlinkages between DeFi participants. Such facilities can be created at the discretion of any individual participant and operate autonomously. Without appropriate consideration of the risks posed to the wider ecosystem, these interlinkages can channel and amplify contagion."
=> 3 canaux identifiés par la Fed : (1) rumeur/déclaration émetteur → redemptions primaires ; (2) PSM/contrats 1:1 autonomes → contagion DAI ; (3) feedback bidirectionnel TradFi ↔ DeFi.

## arXiv 2606.07442 (05 juin 2026) — Sankaewtong, Kitzler, Haslhofer, Ikeda, "Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse"
URL: https://arxiv.org/html/2606.07442v1
Verbatim utiles :
- "Circle, the issuer of USDC, disclosed that approximately USD 3.3 billion, or nearly 8% of its cash reserves, was held at SVB, creating uncertainty about USDC's redeemability."
- "The disclosure triggered a sharp secondary-market depeg of USDC, affected related stablecoins such as DAI and FRAX through direct or indirect collateral links, and coincided with reallocation toward alternative liquidity assets such as USDT and liquidity shifts across USDC-, USDT-, WETH-, and WBTC-related pools."
- "transaction activity across major stablecoins became strongly synchronized during the crisis window, indicating a collective market-level response"
- "a bifurcated contagion pathway. While USDT, WBTC, and WETH reacted primarily as liquidity absorption channels with larger trade volumes, only USDC-related assets exhibited immediate price responses alongside surging transaction counts."
- "driving a mass reallocation from single-coin to multi-coin portfolios"
- Mots-clés : "Blockchain, DeFi, Ethereum, Stablecoin, Financial Contagion, Transaction Networks, Phase Synchronization, Systemic Risk"
=> MÉTHODE : analyse de données transactionnelles haute granularité, extraction de dynamiques de phase, reconstruction du chemin de contagion du niveau marché au niveau compte.

## Chainalysis (2026-04-23) — "Inside the KelpDAO Bridge Exploit"
URL: https://www.chainalysis.com/blog/kelpdao-bridge-exploit-april-2026/
Verbatim utiles :
- "Traditional security tools missed the attack because every on-chain transaction looked completely valid. Spotting this type of exploit requires cross-chain invariant monitoring — continuously verifying that tokens released on a destination chain mathematically match tokens burned on the source chain."
- "The attackers compromised internal RPC nodes and DDoS'd external nodes to feed false data to a single-point-of-failure verification network (a 1-of-1 DVN setup)."
- "Kelp detected the anomaly shortly after it began, paused the relevant contract on Ethereum and its L2 deployments, blacklisted the attacker's addresses, and engaged SEAL-911. Those actions blocked a follow-up attempt in which the exploiter tried to drain an additional 40,000 rsETH (~$95 million) using a second forged 'phantom' packet."
- "Tuesday, three days after the hack, the Arbitrum Security Council moved to freeze a significant portion of the attacker's downstream funds"
- "a community of restakers was left holding tokens whose peg assumptions had quietly been broken"
=> LE VOCABULAIRE CLÉ POUR ORVYREN : "cross-chain invariant monitoring" — vérifier en continu que les invariants comptables inter-chaînes tiennent. C'est exactement une intégration d'information publique multi-canaux.

## FSB (2026-10-12/14) — "Global stablecoin arrangements: Cross-border vulnerabilities and financial stability monitoring"
URL: https://www.fsb.org/2026/10/global-stablecoin-arrangements-cross-border-vulnerabilities-and-financial-stability-monitoring/
- "This note summarises ongoing monitoring work at the FSB on global stablecoin arrangements. In particular, it includes an analysis of the structure of global stablecoin arrangements, the potential propagation of vulnerabilities, and the metrics that could support financial stability monitoring. It also looks at the data currently available for financial stability monitoring of stablecoin activities, assessing the sources as well as the benefits and limitations of these data sources."
- Press release associée 2026-10-12 : "FSB Chair sets out FSB work on AI and stablecoins — Andrew Bailey delivers note on vulnerabilities and monitoring of global stablecoins and finalised sound practices on AI adoption."

## Divers (post-mortems 2026, à vérifier avant citation finale)
- Chainalysis (2026-10-01) : "How AI Helped Chainalysis Investigators Trace the $387 Million North Korea Stole from Bitget". URL: https://www.chainalysis.com/blog/387m-bitget-theft-2026/
- BPI (Bank Policy Institute): "Crypto Hacks and DeFi Runs" — Aave rsETH incident report (governance.aave.com/t/rseth-incident-report-april-20-2026/24580).
