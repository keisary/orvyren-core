# https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices

[Skip to main content](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#main-content)

# Stablecoin Treasury Management: 2026 Best Practices

Allocate, custody, and report on USDC, USDT, USDS, PYUSD, sUSDe across 3-7 chains. Yield ranges 4.1% to 11.8% APY. One-page policy template covering chain mix, issuer mix, custody, and onchain reporting.

Written by Eco
Updated over a month ago

Table of contents

[What Is Stablecoin Treasury Management?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_fa90b45d87)[How Does a Stablecoin Treasury Differ From Traditional Cash Management?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_b7e6b01f88)[Stablecoin Treasury Components](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_06af0562e2)[Allocation Policy](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_7bef0ade0c)[Asset Whitelist](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_ca99e544a1)[Chain Whitelist](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_61857e541d)[Custody Model](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_3b5e722a4b)[Yield Strategy](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_dfb9652213)[Reporting Cadence](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_fcd813f24a)[Operational Workflows](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_746492a7f7)[Receive and Sweep](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_54bdec0108)[Pay Out](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_6cdd4a4e72)[Allocate to Yield](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_defd1dbdbc)[Risk Categories](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_582d021373)[Yield Sources for Stablecoin Treasuries](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_419a93515c)[Multi-Chain Reserve Allocation](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_a434c7ba1f)[Eco's Role in Stablecoin Treasury Workflows](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_7483010351)[FAQ](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_396ea431b7)[What is a stablecoin treasury?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_d0560dd1b8)[How much should a treasury hold in stablecoins versus other assets?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_a3860cfcc4)[What stablecoins are safest for a treasury?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_093f2f3f24)[Can a stablecoin treasury earn yield safely?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_4c6911244c)[How is an onchain treasury reported and audited?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_0303bb3710)

![](https://eco-c1bf1945b488.intercom-attachments-1.com/i/o/bswxc49x/2330825523/af0dfef8c30451b864e4e585c2f2/hero_14799675.png?expires=1792036800&signature=af5f4a75a1af237feaa337c886b8430744af93d1320b8a138c48e983fd2cf599&req=diMkFsF8mIRdWvMW1HO4zT9gAc44YgidvAAYBmysfQVXSbJpgeNeg9MeGIqo%0AXJurEJ6WPZeEQ3400Ac%3D%0A)

Stablecoin treasury management is the practice of holding, allocating, deploying, and reporting on dollar-denominated tokens, primarily USDC, USDT, USDS, PYUSD, and yield-bearing variants like sUSDe, across multiple blockchains, custody surfaces, and counterparties. As of Q1 2026, public companies, DAOs, fintechs, and crypto-native operating businesses collectively hold north of $35B in onchain stablecoin reserves, according to [DeFiLlama's stablecoin dashboard](https://defillama.com/stablecoins). The job has grown beyond "park USDC in Coinbase Custody and forget about it." Treasurers now juggle 3-7 chains, 2-4 stablecoin issuers, multiple custody models, and a real menu of yield options that ranged from 4.1% to 11.8% APY at the time of writing.

​

This guide covers what a stablecoin treasury policy should specify, how to think about chain and asset diversification, where the yield comes from, what custody options exist, and how onchain reporting works in practice. The reader who finishes this should be able to write, or audit, a one-page treasury policy for an operating business or DAO.

​

# What Is Stablecoin Treasury Management?

A stablecoin treasury holds operating cash, reserves, and runway in tokens pegged to the US dollar (or, less commonly, EUR, GBP, or gold) on public blockchains. Three categories of holders dominate the space.

​

**Public companies and corporates.** Stripe, Shopify, MoneyGram, Visa, and PayPal all sit on stablecoin balances either as merchant float or as part of issuer programs. PayPal launched PYUSD in August 2023 and reported over $4B in circulation as of March 2026 per the [Paxos transparency report](https://www.paxos.com/pyusd-transparency/). Stripe agreed to acquire Bridge in October 2024 and [closed the $1.1B deal in February 2025](https://www.cnbc.com/2025/02/04/stripe-closes-1point1-billion-bridge-deal-prepares-for-stablecoin-push-.html), an explicit bet that stablecoin rails will displace card networks for B2B settlement.

​

**DAOs and onchain protocols.** Uniswap's DAO treasury is denominated in UNI and held in the protocol's Governance Timelock; an April 2026 [temp check proposed recalling 12.5M delegated UNI back to that timelock](https://gov.uniswap.org/t/temp-check-return-12-5m-delegated-tokens-to-the-governance-timelock/26099). Aave's Collector Contract aggregated $190M in stablecoin protocol revenue. ENS, MakerDAO (now Sky), Lido, and Optimism each manage nine-figure stablecoin allocations through onchain governance.

​

**Crypto-native operating businesses.** Exchanges, market makers, custodians, and L2 foundations hold operational floats in stablecoins. The Optimism Foundation deployed $200M+ via the Superchain ecosystem in 2025; Coinbase reported $385M in non-custodial stablecoin balances in its [Q4 2025 10-K filing](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001679788).

​

The shared characteristic: cash flow happens in stablecoins natively, so settling out to fiat for management would be expensive, slow, and pointless. The treasurer's job is to manage that float onchain, across chains, without taking principal risk on a depeg or a bridge exploit.

​

# How Does a Stablecoin Treasury Differ From Traditional Cash Management?

The traditional treasury function, sweep balances into money-market funds nightly, ladder T-bills out 13-52 weeks, hold a working balance in operating accounts at one or two banks, translates roughly but not cleanly. Three differences matter.

​

**Settlement is final and instant.** A USDC transfer on Base settles in ~2 seconds with no chargeback path. Treasury operations that depend on settlement timing (T+1, T+2) collapse. This is why Visa, Mastercard, and PayPal have all begun running pilots on Solana and Base, not because they need crypto, but because settlement finality is operationally cheaper.

​

**Custody is configurable, not bundled.** A bank account bundles custody, payments, reporting, and (sometimes) yield. Onchain, those are four independent decisions. A treasurer might custody on Fireblocks, pay through Eco Routes, report through Steakhouse Financial, and earn yield through Maple Finance, four vendors, four contracts, four risk surfaces.

​

**Asset diversification is multi-issuer, not multi-bank.** The bank-equivalent risk for stablecoins is issuer risk: USDC's reserves at SVB during the March 2023 depeg, or USDT's commercial paper exposure pre-2022. [Federal Reserve research from 2024](https://www.federalreserve.gov/econres/feds/files/2024088pap.pdf) shows that issuer concentration is the largest non-protocol risk in stablecoin treasuries. Diversification across USDC, USDT, USDS, and PYUSD reduces that exposure but introduces operational complexity.

​

# Stablecoin Treasury Components

A working treasury operation has six moving parts. Each deserves a policy line.

​

## Allocation Policy

The policy answers: what percentage sits in cash-equivalent stablecoins, what percentage in yield-bearing tokens, what percentage in non-stable assets (governance tokens, BTC, ETH). For a fintech or operating business, the cash-equivalent slice is typically 60-90%. For a DAO holding governance-token revenue, the cash-equivalent slice is usually 20-40%, with the remainder held in the protocol's native token.

​

## Asset Whitelist

Which stablecoins are eligible. A typical 2026 whitelist includes USDC (Circle), USDT (Tether), USDS (Sky, formerly DAI), and PYUSD (Paxos). Yield-bearing variants like sUSDe (Ethena), sUSDS (Sky savings rate), and sFRAX (Frax) appear when the policy allows yield-bearing positions. See the [stablecoin issuer comparison](https://eco.com/blog/stablecoin-comparison) for a current side-by-side.

​

## Chain Whitelist

Which chains can hold the treasury. As of April 2026, the meaningful production chains for stablecoin treasury are Ethereum, Base, Arbitrum, Optimism, Polygon, Solana, Tron, and Avalanche. Each chain has different fee profiles, custody integrations, and DeFi yield surfaces. [Artemis dashboards](https://artemisanalytics.com/) tracked $187B in stablecoin transfer volume across these eight chains in March 2026.

​

## Custody Model

How keys are held: multi-sig (Safe), MPC (Fireblocks, Copper), HSM-backed institutional custody (Coinbase Custody, Anchorage, BitGo), or a hybrid. The choice determines who can sign, how fast they can sign, and what the recovery story looks like.

​

## Yield Strategy


[... middle omitted — see footer ...]

- [Stablecoin Treasury Management: 2024-2026](https://eco.com/support/en/articles/15453927-stablecoin-treasury-management-2024-2026)

Did this answer your question?

Disappointed Reaction😞Neutral Reaction😐Smiley Reaction😃

Table of contents

[What Is Stablecoin Treasury Management?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_fa90b45d87)[How Does a Stablecoin Treasury Differ From Traditional Cash Management?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_b7e6b01f88)[Stablecoin Treasury Components](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_06af0562e2)[Allocation Policy](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_7bef0ade0c)[Asset Whitelist](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_ca99e544a1)[Chain Whitelist](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_61857e541d)[Custody Model](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_3b5e722a4b)[Yield Strategy](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_dfb9652213)[Reporting Cadence](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_fcd813f24a)[Operational Workflows](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_746492a7f7)[Receive and Sweep](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_54bdec0108)[Pay Out](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_6cdd4a4e72)[Allocate to Yield](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_defd1dbdbc)[Risk Categories](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_582d021373)[Yield Sources for Stablecoin Treasuries](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_419a93515c)[Multi-Chain Reserve Allocation](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_a434c7ba1f)[Eco's Role in Stablecoin Treasury Workflows](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_7483010351)[FAQ](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_396ea431b7)[What is a stablecoin treasury?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_d0560dd1b8)[How much should a treasury hold in stablecoins versus other assets?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_a3860cfcc4)[What stablecoins are safest for a treasury?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_093f2f3f24)[Can a stablecoin treasury earn yield safely?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_4c6911244c)[How is an onchain treasury reported and audited?](https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices#h_0303bb3710)

──────── [TRUNCATED] ────────
Showing 10,451 chars (head) + 3,473 chars (tail) of 24,785 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\eco.com-2292b5f744.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\eco.com-2292b5f744.md" offset=96 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────