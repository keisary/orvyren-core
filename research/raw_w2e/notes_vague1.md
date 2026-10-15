# W2-E — Notes brutes (vague 1) — scan concurrentiel agents/automatisations DeFi
Date de collecte : 2026-10-15 (UTC). Toutes les URL sont celles réellement ouvertes/consultées.

## 1. Almanak (agents/vaults DeFi)
- https://almanak.co/ (consulté 2026-10-15) : « Your Agentic Hedge Fund ». Boucle : Build (langage naturel/Python) → Simulate (paper-trade sur fork mainnet) → Deploy (« push it live into your own Safe wallet, with permissions scoped to exactly what the strategy needs ») → Monitor (PnL, health, alertes).
  - CITATION CLÉ (page d'accueil) : « Your funds stay in your Safe. **Zodiac Roles** gives each strategy only the permissions it needs - and keeps everything else off limits. **Safe** custody. **Zodiac**-enforced permissions. »
  - Chaînes affichées : Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche.
  - Investisseurs publics listés : NEAR Foundation, Delphi Labs, HashKey, Bankless Ventures, RockawayX, AppWorks, Matrix Partners China, Sparkle Ventures.
  - « Strategies you can ship today » : leveraged lending & loops (Aave, Morpho, Compound, Spark), concentrated liquidity (Uniswap, Curve, Aerodrome), delta-neutral & basis (GMX perps), multi-protocol one wallet.
  - Agents = **agents de codage** (« Almanak Code ») qui génèrent du code Python de stratégie versionné que l'utilisateur possède ; l'exécution est déterministe.
- https://www.thetokendispatch.com/p/vibecoding-defi-strategies-with-almanaks (19 août 2025) : vault alUSD (Autonomous Liquidity USD) > 27 M$ TVL ; « first community-created vault on Almanak ». « AI agents are bringing that institutional-grade automation to decentralised finance ».
- https://okxventures.medium.com/autonomous-agents-in-defi-transforming-finance-with-ai-522fbde45863 (AMA OKX Ventures, date non affichée dans l'extrait) : « once a deterministic Python strategy is created, you can wrap it in a vault » ; « tokenized AI vaults » ; vaults ERC-7540 (cf. post X cité) ; « The AI agent EOA wallet operates autonomously to execute user-defined strategies ».
- https://almanak.co/tcpp-algo-theory-inc.pdf (doc juridique) : multi-mentions « executed **autonomously by the user** based on user-defined strategies », disclaimers de responsabilité utilisateur.
- **Lecture** : Almanak = la référence la plus proche d'ORVYREN sur la couche « enveloppe » (Safe + Zodiac Roles) mais son cœur produit = **génération de stratégies + vaults tokenisées / rendement**, pas la détection de rupture de risque ni la traçabilité de décision. Le « agent » est un générateur de code + un exécuteur de stratégie déterministe pré-écrite.

## 2. Axal (ex-« Autopilot »)
- https://www.ax.al/autopilot (consulté 2026-10-15) : la page a été RECONVERTIE en produit d'épargne « High Yield Savings » (app iOS/Android), 7.6 % APY cash, 2 % BTC, « Deposits in Axal partner markets 150 M$+ », « Transactions through Axal 1 Md$+ ». Backed by a16z crypto accelerator.
- https://blockworks.com/news/axal-automating-trading-ai-agents (9 avril 2025) : « US-based startup Axal is combining crypto trading with AI agents. They're starting with automated trades through their Autopilot tool, which lets users set a risk tolerance level and other restrictions to automate trading » ; « Autopilot can collect stablecoin yields, engage with DeFi tools, and trade BTC, ETH, memecoins ».
- **Lecture** : Axal a pivoté (2026) du « DeFi agent autonome » vers un produit fintech d'épargne => signe de viabilité économique fragile du modèle « agent trading autonome » grand public. Autonomie encadrée par « risk tolerance »/restrictions (paramètres utilisateur), pas de décision vérifiable publiée.

## 3. Brahma (ConsoleKit / Agentic Protocols)
- https://brahma.fi/blog/bringing-ai-agents-onchain-introducing-the-consolekit (16 janvier 2025) : ConsoleKit = « bridge between AI intelligence and onchain execution ». Architecture : « Brain » (workflow) + smart accounts (Safe) + « modular policy engine ». « every agent has execution capabilities, protected by multiple layers of security » ; « AI models and Agents feed instruction to the Brain, which firstly understands and translates instructions, then preparing an execution environment for the agent, **with its own segregated smart account and strict policies ensuring the agent can't deviate from its mission** ».
  - Safeguards annoncés : « Pre-execution simulation validates transaction success » ; « Customizable rules define precise operating parameters » ; « Post-execution verification confirms successful outcomes ».
  - Chiffres annoncés par Brahma : « securing over $200M in assets, processing $1B+ in volume, and serving 10,000+ accounts » (auto-déclaré).
  - Cas d'usage cités : agents sociaux gérant leur trésorerie (Creator Bid), yield optimization agents, « DAO-agents will allow communities and treasury managers to utilize agents to automate specific operations while maintaining strict security controls ».
- https://decrypt.co/310450/brahma-introduces-agentic-protocols-for-secure-onchain-automation (18 mars 2025) : ConsoleKit « now live with Tempest, Creator.bid, and Swell, and integrated with Morpho » ; « **policy guardrails** ensure all actions remain secure and self-custodial » ; « These Agentic Protocols enable: 24/7 execution across multiple chains without manual intervention ... Automated portfolio management through rebalancing and compounding ... Full user custody through secure, programmable execution with policy guardrails that confine agent actions ».
- https://github.com/Brahma-fi/console-kit : dépôt public (API ConsoleKit, apiKey/baseURL). Docs : https://docs.brahma.fi/
- **Lecture** : Brahma est le concurrent le plus direct sur l'axe « agents bornés on-chain » : smart account dédiée par agent + policy engine + simulation pré-exécution + vérification post-exécution. La différence ORVYREN doit se jouer sur la **détection de rupture de risque dans le graphe de collatéral** et la **traçabilité/recalculabilité de la décision**, pas sur « enveloppe bornée » en soi.

## 4. Griffain
- https://griffain.com/ (consulté 2026-10-15) : « Welcome to Griffain — The Agent Engine ». UI : « Swap tokens with natural language », « @ agents to help you explore the blockchain », wallet via Privy. Sign-in wall.
- https://coinmarketcap.com/cmc-ai/griffain/what-is/ (décr. recherche) : « GRIFFAIN is a Solana-based Web3 platform and ecosystem token designed as an "Agent Engine" that lets users create, customize, ... ».
- https://changelly.com/blog/best-ai-agent-crypto-coins-to-buy/ (2026) : capitalisation GRIFFAIN ~8,3–9 M$, « Solana automation agents », risque « High » => token largement dégonflé vs pic 2025.
- **Lecture** : agent « assistant » Solana à base d'intents/natural language ; pas de gestion de risque de graphe de collatéral, pas de documentation sur bornage (non trouvé à ce stade).

## 5. Wayfinder (Parallel)
- https://reports.tiger-research.com/p/wayfinder-eng : « Wayfinder: On-Chain Specialized AI Agent System ... They automatically perform on-chain tasks » ; agents = « Shells » (cf. https://web3.bitget.com/dapp/wayfinder-24533 : « decentralized AI protocol developed by Parallel that enables autonomous AI agents, known as 'Shells', to navigate and interact with blockchain »).
- https://x.com/AIWayfinder/highlights : « AI agents that execute your onchain strategies autonomously ... giving anyone access to our crypto AI agents to trade, deploy, and discover across chains ».
- **Lecture** : plateforme d'agents on-chain multi-chaînes (navigation web3 + exécution) ; attention détail à confirmer (docs).

## 6. Warden Protocol
- https://wardenprotocol.org/ : « Discover specialised AI agents for trading, investing, and DeFi automation. Think of it as the App Store for Web3 Agents » ; « Warden is the app and network layer for the agent economy, where AI agents trade, manage assets and act onchain on behalf of their users ».
- https://blockeden.xyz/blog/2026/02/02/warden-protocol-ai-agent-coordination-layer-autonomous-economy/ (2 février 2026) : « Warden Buffett: An autonomous, profit-generating trading agent launched in H2 2025 » ; Warden Studio (publier des agents).
- https://www.binance.com/en/square/post/330718707068162 : L1 modulaire Cosmos SDK « specifically engineered for the execution and verification of AI ... ».
- **Lecture** : L1 « agent economy » ; promesses de vérification d'IA au niveau chaîne — concurrent sur l'axe vérifiabilité, à instruire plus finement.

## 7. Modulus Labs
- https://world.org/blog/announcements/modulus-labs-joins-tfh-support-applied-research-world : « Modulus created the world's first verifiable AI projects » ; a rejoint TFH/World (=> pivot/recul du produit DeFi).
- https://x.com/CountableMagic : « 300,000 Eth validator AI risk scores ... One of the largest ZKML apps, ever ».
- https://medium.com/@CountableMagic/chapter-3-the-worlds-first-on-chain-ai-trading-bot-c387afe8316c : historique « on-chain AI trading bot ».
- **Lecture** : ZKML (prouver l'inférence) = brique de « décision vérifiable » **cryptographique** ; coût prohibitif, adoption réelle limitée. À citer comme voie alternative à la vérifiabilité par recalcul (ORVYREN).

## 8. Cod3x (Big Tony)
- https://chainup.com/blog/how-crypto-unlocks-the-true-autonomy-of-ai-agents/ : « Cod3x's flagship AI agent, Big Tony, launched in late 2024, autonomously trading perpetuals on platforms like Hyperliquid ».
- **Lecture** : agent de trading perpétuels (pas gestion de risque de collatéral) ; pas de bornage documenté trouvé.

## 9. Hey Anon (DeFAI)
- https://heyanon.ai/ : « DeFAI Aggregates Everything — Autonomy lives on-chain. Hey Anon connects to every major protocol and yield source, executing actions without friction. It's not just automated, it's orches... » (agent conversationnel + plan + exécution).
- https://www.dwf-labs.com/news/526-heyanon-ai-and-dwf-labs-announce-strategic-partnership-to-pioneer-defai-the-future-of-decentralised-finance : « Autonomous DeFi Agents: Smart AI agents manage wallets and execute multi-step strategies—from bridging tokens to creating liquidity pools ».
- https://forum.heyanon.ai/t/rfc-5-hey-anon-dao-ai-agent-launchpad-applications/132 : « The agent uses HeyAnon's ask pipeline to query on-chain data, portfolio_transactions for wallet behavior ».
- **Lecture** : DeFAI = couche « intents + orchestration » orientée commodité utilisateur, pas surveillance de risque de protocole.

## 10. karpatkey / KPK (gestionnaire pro)
- https://kpk.io/about (consulté 2026-10-15) : « **Non-custodial onchain asset management since 2020**. KPK manages capital for DAOs and institutions through treasury mandates, funds, and vaults. Every strategy runs on the infrastructure we built, and every action is verifiable onchain. »
  - CITATION CLÉ : « karpatkey founded to manage the GnosisDAO treasury. **Operating model established: non-custodial, permission-based asset management via Safe and Zodiac Roles Modifier.** »
  - Jalons : GnosisDAO manager (GIP-20, déc. 2021) ; « karpatkey wins the competitive tender for ENS DAO endowment fund management » ; « Balancer mandate begins ».
- https://kpk.io/blog/kpk-asset-management-framework : « Framework for Active DAO Treasury Execution — Non-Custodial Asset Management in DeFi » ; renvoie à GIP-20 (https://forum.gnosis.io/t/gip-20-karpatkey-dao-treasury-management/2233) et GIP-58.
- https://forum.scroll.io/t/request-for-proposals-dao-treasury-management/1047 : grille tarifaire kpk = « 0.5% management fee on the invested assets under non-custodial management and a 20% performance fee on the yield generated ».
- https://kpk.io/blog/karpatkey-closes-7-million-funding-round (22 oct. 2024) : levée de 7 M$.
- **Lecture** : karpatkey a établi dès 2020-2021 le modèle « Safe + Zodiac Roles Modifier + gestionnaire humain » = **exactement la double enveloppe d'ORVYREN, mais pilotée par des humains**. C'est le concurrent conceptuel le plus proche sur la couche permissions ; ce que karpatkey ne fait pas = automatiser la décision de réduction de risque en continu.

## 11. Steakhouse Financial / Block Analitica / curateurs (gestionnaires pro)
- https://www.steakhouse.financial/ : « The Credit Stack for the Stablecoin Economy — Risk-curated Morpho vaults for treasury and fund capital ».
- https://www.comp.xyz/t/treasury-management-program-primary-allocation/8020 + https://www.linkedin.com/posts/steakhouse-financial_... : Steakhouse sélectionné par Compound : « Steakhouse will curate the noncustodial vault within **DAO-set limits**: capital stays productive and liquid, and remains under DAO control » ; mandat initial jusqu'à ~12 M$ USDC.
- https://blockanalitica.com/ : « Risk Intelligence for DeFi — We provide risk advisory services... ».
- https://x.com/BlockAnalitica : « Risk team behind the @SkyEcosystem's USDS & DAI stablecoins. DeFi risk management since 2019. »
- https://forum.morpho.org/t/block-analitica-b-protocol-flagship-eth-and-usdc-metamorho... (whitelisting des vaults MetaMorpho) : Block Analitica & B.Protocol « partnering as risk curators ... curate transparent and automated lending vaults ».
- https://arxiv.org/html/2512.11976 : « Institutionalizing risk curation in decentralized credit » — analyse de données on-chain oct. 2024 → nov. 2025 sur Aave V2/V3, etc. (article de recherche, utile pour cadrer la curation comme « institutionnalisation »).
- **Lecture** : les curateurs paramètrent des vaults (limites, marchés autorisés) puis **les humains surveillent**. Modèle « DAO-set limits » = bornage par politique hors chaîne mais pas de boucle fermée automatique sur un signal de risque de graphe.

## 12. Chaos Labs quitte Aave (signal fort)
- https://governance.aave.com/t/chaos-labs-is-leaving-aave/24386 (6 avril 2026) : « Today, we are stepping down from that mandate and seeking to proactively terminate our engagement. However, we are leaving because the engagement no longer reflects how we believe risk should be managed. »
- https://www.coindesk.com/tech/2026/04/06/aave-loses-key-risk-manager-chaos-labs-amid-contributor-exodus-and-disputes : Chaos Labs quitte Aave, citant « fundamental misalignment » sur la stratégie de risque, la complexité du V4, et une économie non soutenable malgré une proposition de budget de 5 M$.
- https://finance.yahoo.com/markets/crypto/articles/chaos-labs-exits-aave-crypto-104536551.html : Aave (« $50 billion crypto TVL ») « now operates without a dedicated risk manager » ; Chaos Labs était le risk manager d'Aave depuis novembre 2022 ; troisième contributeur majeur à partir en 2025 après BGD Labs et Aave Chan Initiative.
- https://bitcoinfoundation.org/news/crypto-companies-news/aave-drops-chaos-quits/ : « Chaos Labs is stepping away from Aave after three years, saying the protocol's risk setup no longer fits the job. » AAVE -6 % à ~91,8 $.
- https://governance.aave.com/t/arfc-renew-llamarisk-as-risk-service-provider-epoch-4/24446 : renouvellement LlamaRisk comme risk service provider (epoch 4), dernier message mai 2026.
- **Lecture** : le modèle « risk manager humain sous mandat » est en crise ouverte (économies non soutenables, attrition). Argument fort pour le pitch ORVYREN : automatisation de la surveillance de risque à coût marginal quasi nul.

## 13. Automatisation établie (vague 1)
- Enzyme : https://enzyme.finance/products/blue — « The end-to-end platform manage decentralized strategies — Deploy customizable Enzyme Vaults in seconds with manual, delegated or automated execution. » ; https://enzyme.finance/use-cases/treasury-capital-vaults — « Automate Vault Creation. Enzyme Vaults can be systematically deployed... ».
- DeFi Saver : https://defisaver.com/features/automation — « Crypto is active 24/7. You aren't. » ; automations = Take Profit / Stop Loss, Trailing stop, « A lot of pain going around but thanks to @DeFiSaver I managed to not get liquidated as I have a loan payback automation set to manage my health factor » (témoignage). https://help.defisaver.com/automations/stop-loss-take-profit (« Last updated 2 months ago ») : « configure target price points at which your position would be fully closed ».
- CoW Protocol : https://docs.cow.fi/cow-protocol/concepts/order-types/programmatic-orders — « **Advanced order types**: The conditional nature of programmatic orders allows for complex order types such as stop-loss, good-after-time, take-profit, and more. In fact, CoW Protocol's TWAP orders are built on top of the Programmatic Order Framework. » ; https://docs.cow.fi/cow-protocol/reference/contracts/programmatic/twap ; guide trésoreries DAO : https://cow.fi/learn/twap-orders-for-dao-treasuries-a-practical-guide ; stop-loss via oracles : https://cowswap.mintlify.app/composable-cow/order-types/stop-loss.
- Gelato : https://docs.gelato.cloud/developer-services/web3-functions (« Connect smart contracts to off-chain data & computation ») + https://docs.gelato.cloud/developer-services/automate (« Automate smart contracts with decentralized, reliable execution ») ; https://gelato.cloud/blog/... : « Gelato powers over 400 Web3 projects » ; cas d'usage Pyth : oracle poussé on-chain « every hour or whenever the price changes by 2% or more ».
- Chainlink Automation : https://chain.link/education-hub/smart-contract-automation — « Smart contract automation allows developers to trigger smart contract functions in an automated way. These can include harvesting yield, minting... » ; « Chainlink Automation is a decentralized transaction execution solution that enables smart contracts to automate key functions and DevOps tasks » ; « Chainlink Automation fills the role of waking up smart contracts by issuing on-chain transactions that trigger the smart contract's logic ».
- OpenZeppelin Defender : https://defender.openzeppelin.com/ — « Until the final shutdown on **July 1, 2026**, Defender will remain fully operational while we focus on the open source versions of tools like Relayers and Monitor. » ; https://github.com/OpenZeppelin/defender-sdk — « OpenZeppelin Defender will sunset on July 1, 2026. » **=> l'infrastructure d'automatisation « entreprise » historique est en train de disparaître : opportunité pour un nouvel entrant, mais aussi preuve que le marché de l'automatisation générique est peu rentable.**

## 14. À instruire (vague 2)
- Wayfinder docs détaillées ; Warden verification ; Griffain bornage ; Modulus statut réel.
- Llama (Risk) ; Avantgarde ; Gauntlet (non encore couvert) ; Tally/Znx.
- Paysage concours : hackathons « AI agent + wallet » 2025-2026, gagnants, ce qui impressionne les jurys.
- Question décisive : qui fait déjà (a) décision vérifiable/recalculable, (b) prévision de risque explicite, (c) double enveloppe, (d) abstention documentée ?
