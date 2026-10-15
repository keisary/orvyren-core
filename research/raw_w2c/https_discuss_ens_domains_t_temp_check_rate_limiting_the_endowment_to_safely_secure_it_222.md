# URL: https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234
# fetched: 2026-10-15T03:09:15.243186Z

[Skip to main content](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234#main-container)

- More


Start Here


- [Account Help](https://discuss.ens.domains/g/ForumAccess_Help)
- [Guidelines](https://discuss.ens.domains/guidelines)
- [Documentation](https://docs.ens.domains/dao/)
- [ENS DAO Basics](https://basics.ensdao.org/)
- [Delegate Voting Power](https://delegate.ens.domains/)
- [Vote.ensdao.org](https://vote.ensdao.org/#/)
- [Register your .eth](https://app.ens.domains/)

Categories


- [DAO-Wide](https://discuss.ens.domains/c/dao-wide/48 "Discussion and updates relevant to the ENS DAO.")
- [🗳️ Meta-Governance](https://discuss.ens.domains/c/meta-governance/28 "Discussion of changes to the DAO itself.")
- [🌱 ENS Ecosystem](https://discuss.ens.domains/c/ens-ecosystem/32 "Proposals relating to the ENS ecosystem.")
- [🏛️ Public Goods](https://discuss.ens.domains/c/public-goods/37 "Proposals to fund public goods in the ENS and Ethereum ecosystems.")
- [🧑‍💻 ENS Development](https://discuss.ens.domains/c/ens-dev/42 "Discussion of development of and on ENS.")
- [All categories](https://discuss.ens.domains/categories)

Tags


- [newsletter](https://discuss.ens.domains/tag/newsletter "")
- [All tags](https://discuss.ens.domains/tags)

​


# [\[Temp Check\] Rate limiting the Endowment to safely secure it](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234)

[🗳️ Meta-Governance](https://discuss.ens.domains/c/meta-governance/28) [Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64)

You have selected **0** posts.

[select all](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234)

[cancel selecting](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234)

400
views
12
likes
2
links


[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/avsa/48/1689_2.png)5](https://discuss.ens.domains/u/AvsA "AvsA")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)4](https://discuss.ens.domains/u/nick.eth "nick.eth")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/coltron.eth/48/6949_2.png)](https://discuss.ens.domains/u/Coltron.eth "Coltron.eth")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/katherine.eth/48/7729_2.png)](https://discuss.ens.domains/u/katherine.eth "katherine.eth")

read
10
min


[Jul 1](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234/1 "Jump to the first post")

2 / 11


Jul 1


[Jul 6](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234/11)

## post by AvsA on Jul 1

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/avsa/48/1689_2.png)](https://discuss.ens.domains/u/avsa)

[AvsA](https://discuss.ens.domains/u/avsa)[Delegate](https://discuss.ens.domains/g/delegates)

[Jul 1](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234 "Post date")

# [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-tldr-1) TLDR:

Make a technical lock on the Endowment preventing more than 5% of its current capital to be withdrawn each year. This increases the security of the protocol and safeguards it from hacker attacks or institutional capture and limits the damage that can be done by mismanagement.

## [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-summary-2) Summary

This temp check proposes three linked changes to how the ENS DAO holds and spends its treasury:

1. **A hardcoded annual spending cap on the Endowment.** No more than a fixed amount may leave the Endowment per year — proposed at **5% of the current endowment, adjusted upwards 5% per year**. These limits would be timelocked so while the DAO could remove the caps, doing so would require a months long cooldown.

2. **Consolidating all currently DAO-held ETH and liquid ENS tokens into the Endowment Safe**, behind the same audited permission perimeter that already governs the rest of the Endowment, under a role that does not permit them to be sold or withdrawn (except for any required for currently approved budget).

3. **Plan for a more risk averse 2027 Endowment mandate** that targets a conservative 5% yearly to reach a self sustainable level.


The goal is to solve two problems with one mechanism: **drastically shrink the treasury’s attack surface**, and **give the DAO a disciplined, predictable fiscal policy**. Crucially, the design is _intent-free_ — it bounds how much value can leave per year regardless of who is trying to move it or why, which is exactly the property our current defenses lack. This proposal is intentionally focused on _treasury security_ rather than governance reform. It should be understood as one constitutional safeguard within a broader governance architecture not as complete solution to governance capture. It is meant to protect the treasury from either malevolent attacks or just plain bad fund management.

This is deliberately a simple, boring mechanism. The simplicity is the security.

* * *

## [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-background-the-problem-3) Background: the problem

## [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-image624x289uploadiwgr4vntuewtsew482gnxoylkqjpng-4)   [![image](https://discuss.ens.domains/uploads/db9688/optimized/2X/8/81ccd416760b0117b4ba3d5bbfa7b30bb887e011_2_624x289.png)\ image1118×518 57.8 KB](https://discuss.ens.domains/uploads/db9688/original/2X/8/81ccd416760b0117b4ba3d5bbfa7b30bb887e011.png "image")

The DAO’s assets sit in three places today:

- The **Endowment**: ETH, stablecoins and liquid-staking positions, actively managed by karpatkey through a Zodiac Roles perimeter on a DAO-owned Safe.

- The **DAO timelock and registrar controllers**: the operating float in ETH and stables.

- **55M ENS tokens** — the DAO’s own governance tokens, with 9.8M currently held in the wallet.ensdao.eth and another 45M already fully unlockable in the time lock contract.


We face two distinct problems that, it turns out, have the same fix.

### [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-problem-1-security-5) Problem 1 — Security

ENS is a token-weighted DAO whose treasury is worth far more than the cost of acquiring a working voting majority. That asymmetry is the root governance-attack risk, and it has been understood since at least 2023.

The Security Council is one layer of defense, but it might be more fragile than previously thought. Currently it is near its end of life and there are two competing proposals to renew it, differing mostly in how each defines what is considered an attack. This proposal sidesteps this by making the simplest mode of a DAO attack, a proposal that requests the treasury, 95% less profitable.

### [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-problem-2-fiscal-discipline-6) Problem 2 — Fiscal discipline

Separately, and less dramatically: the DAO has no structural ceiling on its own spending. Draws happen proposal by proposal. An endowment exists to _preserve a corpus and spend only a sustainable slice of it_ — that is the entire point of the institution — and right now nothing enforces that discipline at the contract level. This year there has been a dramatic change in the structure of working groups and there’s an active discussion on how to better structure the foundation moving forward. This proposal ensures that, no matter how the issue is resolved, the Endowment cannot be drained by a failure in governance.

* * *

## [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-the-security-case-7) The security case

A spending cap defends the treasury in precisely the case the Security Council cannot: it does not care who the attacker is, how they acquired their votes, or what they intend. It simply bounds the amount of value that can leave per year.

- A hard cap per year means that even a successful, undetectable, majority-controlled drain extracts at most one year’s budget line — on the order of a **95% reduction in the single-year profitability** of an attack on the liquid treasury.

- It makes the “remove the Council, then drain” sequence pointless. The cap binds regardless of who holds which roles, so capturing the cancel mechanism buys an attacker nothing.

- It converts the hardest, most dangerous attack (a quiet, hedged, attribution-proof accumulation) from “drain the treasury” into “extract one capped year and wait a year for the next” — under a one-year cooldown that is fully public and gives the community, and the price, a long window to respond.

- Under the proposal, the most an attacker could extract in a year (~$6M) is comparable to the value of ENS that is being actively used for voting in proposals


**Consolidating ENS into the Endowment closes the biggest remaining hole.** Today the governance-token position is our least-protected asset. Moved into the Endowment Safe, it sits behind the same battle-tested Zodiac perimeter as everything else and simply cannot be swept by a hostile proposal. This is the more important half of the proposal, and the one I expect the most discussion on.

* * *

## [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-the-fiscal-case-8) The fiscal case

The same mechanism is also just good treasury policy.

- **5% of the current Endowment is ~$6M which is roughly our current annual operating envelope.** Setting the cap there forces us to budget to a sustainable number rather than treating the corpus as spendable.

- **A 5%/year escalator** approximates long-run inflation plus modest real growth, giving working groups, service providers and the Foundation a predictable multi-year planning figure.

- **Re-votable every five years** so the policy adapts to genuine changes in scale or cost — but on a deliberately slow cadence, not a casual one.


### [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-how-the-cap-is-calculated-9) How the cap is calculated

The cap will set by looking at 5% of the endowment at the time of the proposal execution (which would be about 6 million dollars at the current state) and hard coding that as the cap, which is then increased slowly by 5% yearly.

Initially this proposal explored the idea of having the cap float to always be 5% of the total value of the Endowment at any point, so that reasonable conservative investments could offset them. A live percentage of total value has two main drawbacks:

1. **It requires an on-chain valuation of an actively-managed, multi-protocol portfolio** — which means either a manually-entered number (a trust hole) or a complex valuation oracle (an audit and manipulation surface).

2. **A percentage cap floats _up_ in a bull market** — i.e. it gets _looser_ at exactly the moment an attacker’s buy-and-drain is cheapest to execute. That is precisely backwards.


A hardcoded, time-indexed schedule — cap = 6M × 1.05^(years elapsed) — needs no oracle, cannot be inflated by a price pump, is trivial to compute, and is dramatically cheaper to audit. It is strictly more conservative in the scenario that matters and it’s both similar to 5% of the current Endowment and our current operation budget.

* * *

## [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-mechanism-high-level-10) Mechanism (high level)

The intent is to **reuse existing, audited primitives** rather than deploy new custom contracts:

- Implemented via **Zodiac modules on the existing Endowment Safe** — the same stack KPK already operates, which already includes an Allowance Module with periodic resets.

- A **cap module** enforces the escalating annual schedule on value _leaving_ the Endowment, based on current market value of the outgoing asset.

- The module limits the types of tokens that can be withdrawn to a few select USD Stables (which count to the cap) or ENS (which also have their own separate 5% cap)

- It means the DAO pays budgets in USD stables only\*, and it’s up to the endowment manager to make sure there are enough to be swapped

- A **Delay Modifier** enforces the one-year cooldown on any over-cap action — and, critically, **gates its own removal and reconfiguration**, so the self-binding is real and there is no fast path around the delay.

- **In-perimeter activity is unaffected.** Swaps, deposits, rebalancing and yield strategies that keep value inside the fund do not count against the cap; only value exiting the Endowment does.

- The cap would be proportional to the last time it was executed, so the limit could be applied either yearly, quarterly or monthly, depending on the DAO needs.


\\* _Alternatively, the cap could be based on market value of any token at the moment of transfer but this adds the requirement of having on chain oracles again, which adds a target for attack._

Relying on Zodiac is a feature, not a compromise: it is in production on this exact Safe, has live bug bounties, and is far simpler to review than a bespoke treasury vault.

This is only the amount that can be withdrawn from the endowment, if it’s insufficient for running the operations, it can be complemented using ENS revenue (although we recommend always focusing on depositing part of it back to the endowment), sponsorships, conferences – or cost cutting to reach the target.

## [Heading link](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234\#p-61862-endowment-mandate-2027-11) Endowment mandate 2027

Recently the DAO approved Karpatkeys latest “ [2026 Endowment Policy update”](https://snapshot.box/#/s:ens.eth/proposal/0x0b5fde95f53bbcda7935cdc0d29c852f3447cc324a618b031bd6f4ec3a0aeee0) a long detailed document that might have been overlooked by some delegates under other debates. The approved policy update states that the vision for the endowment is divided in:

> _Medium-term (0–5 years): capital growth and optimised deployment toward institutional-grade onchain strategies that enhance yield without compromising capital preservation, liquidity, or ENS’s values._
>
> _Long-term (5+ years): capital preservation as the dominant objective, with risk appetite shifting downward as the Endowment matures toward self-sustainability._


[... middle omitted — see footer ...]


In that event I’m not sure why a new mechanism would be required - the security council already gates all DAO proposals. What I was proposing was a mechanism by which the security council would have both the technical and social criteria required to screen and approve any withdrawals from the endowment made by the foundation, without requiring encoding everything in code, which I think we both agree is impractical at the moment.

## post by AvsA on Jul 6

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/avsa/48/1689_2.png)](https://discuss.ens.domains/u/avsa)

[AvsA](https://discuss.ens.domains/u/avsa)[Delegate](https://discuss.ens.domains/g/delegates)

[Jul 6](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234/10 "Post date")

[@nick.eth](https://discuss.ens.domains/u/nick.eth) I am not sure I understand your position. So let me restate it.

Would you agree, to enact new policies (regardless if they’re political, or technical) to make sure that the Endowment (regardless who is managing it) stays majoritally onchain and no one can withdraw more than a given % of it per year?

## post by nick.eth on Jul 6

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)](https://discuss.ens.domains/u/nick.eth)

[nick.eth](https://discuss.ens.domains/u/nick.eth)[Delegate](https://discuss.ens.domains/g/delegates)

[Jul 6](https://discuss.ens.domains/t/temp-check-rate-limiting-the-endowment-to-safely-secure-it/22234/11 "Post date")

I would certainly agree to enact new policies that limit how much of the endowment can be spent in a given year. Long term sustainability is the whole purpose of the Endowment and it makes sense to enforce it if we can.

I don’t think it’s wise to hard-lock it to being _onchain_ custody; while it’s definitely best to explore onchain yield options first, where offchain options exist that are significantly better or safer, and have reliable custodians available, we should be free to consider them for a portion of the endowment.

Reply

### New & Unread Topics

| Topic | Replies | Views | Activity |
| --- | --- | --- | --- |
| [\[EP 6.38\] \[Executable\] Endowment permissions to karpatkey - Update #8](https://discuss.ens.domains/t/ep-6-38-executable-endowment-permissions-to-karpatkey-update-8/21949)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [3](https://discuss.ens.domains/t/ep-6-38-executable-endowment-permissions-to-karpatkey-update-8/21949/1) | 133 | [Mar 19](https://discuss.ens.domains/t/ep-6-38-executable-endowment-permissions-to-karpatkey-update-8/21949/4) |
| [Update on the Endowment Fee Structure (Metagov + kpk)](https://discuss.ens.domains/t/update-on-the-endowment-fee-structure-metagov-kpk/21684)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [1](https://discuss.ens.domains/t/update-on-the-endowment-fee-structure-metagov-kpk/21684/1) | 336 | [Dec 2025](https://discuss.ens.domains/t/update-on-the-endowment-fee-structure-metagov-kpk/21684/2) |
| [\[EP 6.27\] \[Executable\] Endowment permissions to karpatkey - Update #7](https://discuss.ens.domains/t/ep-6-27-executable-endowment-permissions-to-karpatkey-update-7/21641)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [6](https://discuss.ens.domains/t/ep-6-27-executable-endowment-permissions-to-karpatkey-update-7/21641/1) | 383 | [Dec 2025](https://discuss.ens.domains/t/ep-6-27-executable-endowment-permissions-to-karpatkey-update-7/21641/7) |
| [Toward Sovereign Governance: Reducing Reliance on Extrinsic Assets and the Security Council](https://discuss.ens.domains/t/toward-sovereign-governance-reducing-reliance-on-extrinsic-assets-and-the-security-council/21768)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [0](https://discuss.ens.domains/t/toward-sovereign-governance-reducing-reliance-on-extrinsic-assets-and-the-security-council/21768/1) | 95 | [Jan 4](https://discuss.ens.domains/t/toward-sovereign-governance-reducing-reliance-on-extrinsic-assets-and-the-security-council/21768/1) |
| [Expanding the Endowment Mandate: Onchain Options](https://discuss.ens.domains/t/expanding-the-endowment-mandate-onchain-options/22239)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [14](https://discuss.ens.domains/t/expanding-the-endowment-mandate-onchain-options/22239/1) | 606 | [Aug 17](https://discuss.ens.domains/t/expanding-the-endowment-mandate-onchain-options/22239/15) |

Topic list, column headers with buttons are sortable.

### Want to read more? Browse other topics in [Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) or [view latest topics](https://discuss.ens.domains/latest).

[Powered by Discourse](https://discourse.org/powered-by)

Invalid date

Invalid date

──────── [TRUNCATED] ────────
Showing 14,968 chars (head) + 4,994 chars (tail) of 38,667 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\discuss.ens.domains-aac2d21c22.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\discuss.ens.domains-aac2d21c22.md" offset=209 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────