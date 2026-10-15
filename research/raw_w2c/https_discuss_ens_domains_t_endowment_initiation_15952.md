# URL: https://discuss.ens.domains/t/endowment-initiation/15952
# fetched: 2026-10-15T02:59:13.327595Z

[Skip to main content](https://discuss.ens.domains/t/endowment-initiation/15952#main-container)

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


# [Endowment initiation](https://discuss.ens.domains/t/endowment-initiation/15952)

[🗳️ Meta-Governance](https://discuss.ens.domains/c/meta-governance/28) [Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64)

You have selected **0** posts.

[select all](https://discuss.ens.domains/t/endowment-initiation/15952)

[cancel selecting](https://discuss.ens.domains/t/endowment-initiation/15952)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/1 "Jump to the first post")

2 / 37


Jan 2023


[Feb 2023](https://discuss.ens.domains/t/endowment-initiation/15952/39)

## post by kpk on Jan 20, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/kpk/48/13441_2.png)](https://discuss.ens.domains/u/kpk)

[kpk](https://discuss.ens.domains/u/kpk)

2

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952 "Post date")

# [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-summary-1) Summary

This proposal aims to initiate the Endowment by requesting the ENS DAO to transfer 10,766 ETH to a newly created SAFE provided by kpk and owned by the DAO.

This transfer represents the first installment of a series of three equal monthly transfers until the Endowment reaches its full funding goal.

# [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-abstract-2) Abstract

This proposal builds on a [previous post](https://discuss.ens.domains/t/social-endowment-initial-conditions-required-steps/15684) outlining the initial conditions and steps for creating the Endowment. It provides updated information reflecting current market conditions, and covers the following topics:

1. A summary of the previous post

2. The size of the Endowment and allocation rate

3. Strategies and projected results

4. Technical implementation


- A list of Zodiac Roles Modifier permissions for the Manager Role
- Future permissions and roles
- Next steps

5. Additional requirements for the creation of the Endowment.

# [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-specification-3) Specification

## [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-a-summary-of-the-previous-post-4) A summary of the previous post

The previous post presented the following topics regarding the Endowment:

1. The Endowment will consist of the entire treasury, minus $16,000,000, which is equivalent to two years of expenses for the DAO. This amount was discussed in the [‘Routine DAO treasury management’ post](https://discuss.ens.domains/t/social-routine-dao-treasury-management/15501).

2. The DAO will keep unearned ETH as is and convert all remaining funds to USDC.

3. To take a cautious approach, the Endowment will be seeded gradually.

4. kpk will implement two types of risk-adjusted strategies using reputable and proven protocols:


- _USD-neutral_ stablecoin strategies aimed at earning a positive return measured against USD.
- _ETH-neutral_ ETH and derivatives strategies aimed at earning a positive return measured against ETH.

5. 100% of the rewards will be converted to stablecoins and re-invested in USD-neutral strategies.

## [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-size-of-the-endowment-5) Size of the Endowment

The breakdown of the total funds currently held by the DAO is:

| Total account balances |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Token** | **Description** | **Amount** | **Price** | **Value** |
| ETH | Unearned (controller) | 18,971 | $ 1,593.00 | $ 30,220,962 |
| ETH | Earned (controller) | 17,731 | $ 1,593.00 | $ 28,245,021 |
| ETH | DAO | 4,091 | $ 1,593.00 | $ 6,517,409 |
| USDC | DAO | 2,467,026 | $ 1.00 | $ 2,467,026 |
| **Total** |  |  |  | **$ 67,450,419** |

The DAO plans to establish a separate fund to cover expenses for two years, estimated at $16,000,000. This will be achieved by keeping USDC in the DAO’s wallet and converting the required earned ETH into USDC.

| 2-year Runway Fund |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **Token** | **Description** | **Destination** | **Amount** | **Price** | **Value** |
| USDC | DAO | ENS main wallet | 2,467,026 | $ 1.00 | $ 2,467,026 |
| ETH | Earned (controller) | ENS main wallet | 8,495 | $ 1,593.00 | $ 13,532,974 |
| **Total** |  |  |  |  | **$ 16,000,000** |

The remaining ETH will be sent to the Endowment. kpk will manage the unearned ETH by deploying it into ETH-neutral strategies. Earned and DAO’s ETH will be gradually converted to USDC. After discussing with the ENS stewards, we decided that it would be more efficient for the ENS DAO to transfer all funds in ETH to the Endowment and then grant kpk specific permission to handle the gradual conversion to USDC.

| Endowment assets |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **Token** | **Description** | **Destination** | **Amount** | **Price** | **Value** |
| ETH | Unearned (controller) | Endowment | 18,971 | $ 1,593.00 | $ 30,220,962 |
| ETH | Earned (controller) | Endowment | 9,235 | $ 1,593.00 | $ 14,712,047 |
| ETH | DAO | Endowment | 4,091 | $ 1,593.00 | $ 6,517,409 |
| **Total** |  |  | **32,298** |  | **$ 51,450,419** |

After converting the earned and DAO’s ETH into USDC, the approximate resulting balance is as follows:

| Endowment assets |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| **Token** | **Description** | **Destination** | **Amount** | **Price** | **Value** | **Share %** |
| ETH | Unearned | Endowment | 18,971 | $ 1,593.00 | $ 30,220,962 | 59% |
| USDC | - | Endowment | 21,229,456 | $ 1.00 | $ 21,229,456 | 41% |
| **Total** |  |  |  |  | **$ 51,450,419** | **100%** |

[![](https://discuss.ens.domains/uploads/db9688/optimized/2X/b/bc6e7fe60184b285bfb8179569c044d9ed39eb41_2_508x313.png)\\
Chart1200×742 29.4 KB](https://discuss.ens.domains/uploads/db9688/original/2X/b/bc6e7fe60184b285bfb8179569c044d9ed39eb41.png "Chart")

It should be noted that these figures are approximate and the final numbers will depend on the price of ETH at the time of each swap.

## [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-seeding-rate-6) Seeding rate

The Endowment’s construction will be done moderately, starting with a portion of the funds and gradually increasing to 100% as kpk demonstrates their capabilities and meets their commitments outlined in the Fund management proposal. After consulting with the ENS Stewards, it was decided that the most suitable approach is to seed the Endowment in three equal monthly installments of 33%. This approach allows the ENS DAO enough time to evaluate progress before committing all the funds while minimizing opportunity cost for the Endowment.

The first installment will be carried out through this executable proposal and the second and third installments will be executed through new proposals that will be posted on the forum in a timely manner.

After the ENS DAO seeds the Endowment with the first installment of 10,766 ETH, kpk will convert approximately 41% of it into USDC, creating the following initial scenario for deploying the intended strategies:

| Initial Scenario |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| **Token** | **Initial %** | **Initial amount** | **Price** | **Initial Value** | **Share %** | **Strategy** |
| ETH | 33% | 6,324 | $1,593.00 | $ 10,073,644 | 58.7% | ETH - neutral |
| USDC | 33% | 7,076,478 | $1.00 | $ 7,076,478 | 41.3% | USD - neutral |
| **Total** |  |  |  | **$ 17,150,122** |  |  |

## [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-strategy-and-projected-results-7) Strategy and projected results

The list below shows the strategy that kpk will initially deploy after the Endowment has been seeded. The final allocation may vary depending on the current market conditions at the time of deployment.

| # | Protocol | Assets | Strategy | Share per Strat | Allocated Funds | Share of Portfolio | Proj. APR | Proj. Rev | Pool TVL <br>(MM) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Compound v2 | DAI | USD - neutral | 50% | $ 3,538,239 | 20.63% | 2.02% | $ 71,472 | $465 |
| 2 | Compound v2 | USDC | USD - neutral | 50% | $ 3,538,239 | 20.63% | 2.04% | $ 72,180 | $539 |
| 3 | Aura Finance | wstETH - WETH | ETH - neutral | 40% | $ 4,029,458 | 23.50% | 10.21% | $ 411,408 | $162 |
| 4 | Curve | stETH - ETH | ETH - neutral | 40% | $ 4,029,458 | 23.50% | 6.37% | $ 256,676 | $1,400 |
| 5 | Stakewise/ Uniswap v3 | sETH2 - ETH | ETH - neutral | 20% | $ 2,014,729 | 11.75% | 15.81% | $ 318,529 | $62 |
|  | **Total** |  |  |  | **$ 17,150,122** | **100.00%** | **6.59%** | **$ 1,130,265** |  |

If implemented, the projected annual results for the presented strategies are:

| Annual results |  |
| --- | --- |
| Total Funds | $ 51,450,419 |
| Utilized Funds | $ 17,150,122 |
| Capital Utilization | 33.33% |
| Gross Revenues | $ 1,130,265 |
| Gross APR | 6.59% |
| Management Fee <br>(calculated over AUM) | 0.50% |
| Performance Fee <br>(calculated over revenue) | 10% |
| **Net Revenues** | **$ 931,488** |
| **Net APR** | **5.43%** |

After the launch of the Endowment, kpk will conduct a thorough review of the strategy before the transfer of any new installment. If an expansion is recommended, the necessary permissions will be promptly provided for a new on-chain vote. The transfer of the new installment and the corresponding modifications to the preset will be executed simultaneously in accordance with established protocols.

## [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-technical-implementation-8) Technical implementation

### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-a-list-of-zodiac-roles-modifier-permissions-for-the-manager-role-9) A list of Zodiac Roles Modifier permissions for the Manager Role

The non-custodial solution for managing the Endowment relies on a proxy Management SAFE and the Zodiac Roles Modifier. The Zodiac Roles Modifier limits kpk’s actions by only allowing the execution of predetermined transactions defined by the allowlisted preset or role.

A preset or role is a set of permissions for specific smart contract functions that need to be applied by the Endowment’s owner (the DAO) through a batch of specific transactions. Once executed, kpk can operate the Manager SAFE in accordance with the granted permissions. The Manager Role preset, which contains all required permissions for the strategy outlined, can be found in the [Annex Document](https://docs.google.com/document/d/11xrliJIveXO6C6twYOrnGJ5QUW0Apr1LCcDY8hOfpuo/edit?usp=sharing).

To simplify the setup process for the ENS DAO, kpk proposes to take responsibility for creating the new SAFE and applying the Manager Role outlined in the Annex Document. More details can be found in the Next Steps section.

### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-future-permissions-and-roles-10) Future permissions and roles

In order to adapt to changing market conditions, new permissions may be required. For example, if a particular strategy no longer provides sufficient yield or a pool in which the ENS DAO has a position becomes deprecated and needs to be migrated. New roles may also be needed to improve or expand operations. Two new roles are planned for the near future: the _Harvester Role_ and the _Swapper Role_. Both roles will be granted specific subsets of the Manager preset permissions and will be assigned to EOAs to automate certain tasks. The Harvester Role will be allowed to claim rewards, while the Swapper Role will be allowed to swap these rewards for ETH or stablecoins.

When deemed appropriate, kpk will create a new forum post requesting the ENS DAO to update the preset or deploy new roles. The post will include an explanation of why the permissions and/or roles are needed and the executable payload. The proposal will need to be passed by the community and, once approved, it will be executed according to the DAO standard operating practices. To minimize opportunity cost, the process should be as simple and straightforward as possible. A summary of the new permissions and/or roles will be included as a separate section in every corresponding weekly report.

### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-next-steps-11) Next Steps

To simplify the process for the ENS DAO, the proposed implementation steps are:

1. kpk will create a new SAFE, deploy the Roles Modifier contract, and apply the Manager Role preset (as outlined in the Annex Document).

2. kpk will conduct a small-scale replication of the strategy for further testing. ENS stewards are invited to participate in this process.

3. Once the SAFE is created, tested, and permissions are applied, kpk will transfer ownership of it to the ENS DAO and remove themselves as owner.

4. This proposal will be submitted to on-chain voting.

5. If approved, the first transfer will be executed.


## [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-additional-information-12) Additional information

### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-audits-13) Audits

Audits have been conducted on the Zodiac Roles Modifier to ensure its security and functionality. The first audit was completed by G0, and the official report can be found [here](https://github.com/gnosis/zodiac-modifier-roles/blob/main/packages/evm/docs/ZodiacRolesModifierJan2022.pdf). Additionally, Ackee and Sub7 have recently conducted external audits and found no critical issues. The official reports will be released shortly and shared with the community for review.

### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42188-ens-endowment-subgroup-14) Ens-endowment subgroup

To integrate the Endowment into the existing structure of the DAO, a subgroup called ens-endowment must be created. Please note that it was previously referred to as the Finance Core Unit but has recently been renamed to align with ENS’s current naming conventions.

The ens-endowment subgroup will be attached to the [ENS DAO podarchy](https://pod.xyz/podarchy/ensdao) with the assistance of Metropolis. kpk will create the ens-endowment pod consisting of the Manager SAFE through the [Metropolis app](https://pod.xyz/). Three fund managers from kpk will be appointed as members of the pod and the [ENS-metagov pod](https://pod.xyz/ens-metagov) will be set as the subgroup manager, with the power to add and remove members at any time. The ens-endowment role will be limited by the permissions granted to the Manager SAFE through the application of the permissions set in the Manager Role.

To be clear: the SAFE which holds the endowment funds will not be a pod. Rather, the SAFE which has the permission to execute specific transactions on the Endowment SAFE will be a pod, which gives ENS ultimate control over who has access to manage the endowment funds.

Below are two slides borrowed from the Metropolis’ presentation that offer more information about the intended structure. Thanks to the Metropolis team for your collaboration.

[![](https://discuss.ens.domains/uploads/db9688/optimized/2X/5/5a89b06e5b5301ff20c9a8da356495308597a11e_2_624x351.jpeg)\\
1600×900 126 KB](https://discuss.ens.domains/uploads/db9688/original/2X/5/5a89b06e5b5301ff20c9a8da356495308597a11e.jpeg "")

[![](https://discuss.ens.domains/uploads/db9688/optimized/2X/9/9fee7dbd74a00fce96b5f69c2d52292cb8c7a7cc_2_624x351.png)\\
960×540 73.7 KB](https://discuss.ens.domains/uploads/db9688/original/2X/9/9fee7dbd74a00fce96b5f69c2d52292cb8c7a7cc.png "")

- [\[EP3.4\] \[Executable\] Fund the Endowment (first tranche)](https://discuss.ens.domains/t/ep3-4-executable-fund-the-endowment-first-tranche/16277)
- [Endowment Weekly Reports](https://discuss.ens.domains/t/endowment-weekly-reports/16665)
- [ENS DAO Newsletter #28 - 02/01/2023](https://discuss.ens.domains/t/ens-dao-newsletter-28-02-01-2023/16196)
- [Real-World Assets discussion](https://discuss.ens.domains/t/real-world-assets-discussion/17520/2)
- [Karpatkey 2023 Review for the ENS Endowment](https://discuss.ens.domains/t/karpatkey-2023-review-for-the-ens-endowment/18656)
- 5 more

6.4k
views
88
likes
18
links
14
users


[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)9](https://discuss.ens.domains/u/nick.eth "nick.eth")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/santinomics.eth/48/7178_2.png)5](https://discuss.ens.domains/u/santinomics.eth "santinomics.eth")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/james/48/506_2.png)5](https://discuss.ens.domains/u/James "James")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/alisha.eth/48/8743_2.png)4](https://discuss.ens.domains/u/alisha.eth "alisha.eth")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/garypalmerjr/48/949_2.png)3](https://discuss.ens.domains/u/garypalmerjr "garypalmerjr")

read
21
min


## post by 184.eth on Jan 20, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/184.eth/48/13946_2.png)](https://discuss.ens.domains/u/184.eth)

[184.eth](https://discuss.ens.domains/u/184.eth)[Delegate](https://discuss.ens.domains/g/delegates)

1

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/2 "Post date")

I recall there are two(?) types of service fees charged by Karpatkey. Would you please share these again in thread?

Regarding

- unearned ETH kept as ETH
- Karpatkey will manage the unearned ETH by deploying it into ETH-neutral strategies
- ETH-neutral strategies aims at positive return measured against
- service fees

Is my understanding correct that service fees on unearned-eth (held in eth-neutral strategy) will be applied against profit portion (using the following example to explain the question).

With a 12 months reporting period.

For funds in eth-neutral-strategy.

Opening Balance 2000e

Beginning price of ETHUSD=1000

Ending price of ETHUSD-1500

Closing Balance 2300e

.: fee applied to 450k USD (300e \*$1500)

And that if any loss is incurred within the eth-neutral strategy, this would incur no fee & instead the negative balance then rolls over to offset to USD-neutral strategy’s performance? (using the following second-example to explain the question)

With a 12 months reporting period.

For funds in eth-neutral-strategy.

Opening Balance 2000e

Beginning price of ETHUSD=1000

Ending price of ETHUSD-1500

Closing Balance 1900e

.: No fee on eth-neutral strategy,

.: negative 150k USD (100e \*$1500) offsets performance in usd-neutral strategy.

Cheers

## post by alisha.eth on Jan 21, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/alisha.eth/48/8743_2.png)](https://discuss.ens.domains/u/alisha.eth)

[alisha.eth](https://discuss.ens.domains/u/alisha.eth)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/3 "Post date")

Can you please specify the timing and method of sale you plan to use to sell the ETH into USDC?

If the plan is to sell the ETH in the immediate future, I have concerns that with James’ proposal to sell 10,000 ETH to secure 24 months’ runway and your plan to sell ~4414 ETH, the DAO would be liquidating 35% of its ETH in a very short amount of time.

## post by santinomics.eth on Jan 23, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/santinomics.eth/48/7178_2.png)](https://discuss.ens.domains/u/santinomics.eth)

[santinomics.eth](https://discuss.ens.domains/u/santinomics.eth)

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/184.eth/24/13946_2.png)184.eth](https://discuss.ens.domains/t/endowment-initiation/15952 "Load parent post")

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/4 "Post date")

Hello 184.eth, my name is Santi from Karpatkey. I would like to provide additional information to clarify the fees situation. According to [EP 2.2.5](https://discuss.ens.domains/t/updated-endaoment-proposal-karpatkey-steakhouse-financial/14799), Karpatkey charges two types of fees that are fully nominated and collected in ETH:

1. _Management fee_: 0.5% of the nAUM (non-custodial assets under management). This fee is calculated as follows: Management fee = Weekly portfolio balance (in US dollar terms at the time of the report) \* 0.5% / 52, converted to ETH priced at the moment of issuing the report.
2. _Performance fee_: 10% of the yield obtained during the previous week, converted to ETH priced at the moment of issuing the report.

Please note that the performance fee is only applied to the yield obtained on a weekly basis. Unless there’s a problem with one of the ETH-neutral strategies or the ETH derivatives, the positions should never yield a negative result. The calculation takes into account the APR by considering the return on invested capital and any additional rewards. All calculations are nominated in US dollar and then converted into ETH using the prices stated in the report. 10% of the resulting ETH is the performance fee.

For more information, you can refer to the Gnosis DAO [report](https://drive.google.com/file/d/1zql9pI9HDFw_JmzjANXT_OPFNrDI3c_f/view) recently issued by Karpatkey.

- [Kpk H1 2025 Review for the ENS Endowment](https://discuss.ens.domains/t/kpk-h1-2025-review-for-the-ens-endowment/21055/3)

## post by santinomics.eth on Jan 23, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/santinomics.eth/48/7178_2.png)](https://discuss.ens.domains/u/santinomics.eth)

[santinomics.eth](https://discuss.ens.domains/u/santinomics.eth)

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/alisha.eth/24/8743_2.png)alisha.eth](https://discuss.ens.domains/t/endowment-initiation/15952 "Load parent post")

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/5 "Post date")

Hello Alisha!

Karpatkey’s plan is to sell the ETH within a few days of receiving the first transfer, in order to deploy the resulting USDC in USD-neutral strategies, as outlined in the post. We will repeat this process with each installment received. After two months, we anticipate having sold approx. 13,327 ETH for USDC.

In regards to the method, Karpatkey will select the most efficient whitelisted pool at the time of the swap. Currently, this would be done through the WETH-USDC pool on Uniswap v3. To minimize slippage, we may divide the swap into smaller transactions, though the quantity in question should not result in significant slippage.

## post by alisha.eth on Jan 23, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/alisha.eth/48/8743_2.png)](https://discuss.ens.domains/u/alisha.eth)

[alisha.eth](https://discuss.ens.domains/u/alisha.eth)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/6 "Post date")

.. so it’s not 35% of the DAO’s ETH that will be sold in the immediate future, but rather 58%? Is that correct?

#### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42251-strategy-1) Strategy

Why would you not adopt a DCA strategy here? Can you please explain why there is such a rush to sell the ETH into USDC, other than it being part of your strategy?

#### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42251-december-sell-scenario-2) December Sell Scenario

Had this proposal gone to a vote in December (which was discussed), the average sale price of ETH would have been ~$1,200. If 4,442 ETH had been sold at that time, it would have generated 5,330,800 USDC. With a rate of return of 2.04% on USDC, that would yield ~$108,748 over the following year.

#### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42251-january-sell-scenario-3) January Sell Scenario

If that same proposal is put to a vote now, the average sale price might be closer to ~$1600. So, 4,442 ETH sold at $1,600 would generate 7,107,200 USDC.

The difference in a single month, on the FIRST installment is $1.7m. Had the first sale price of $1,200 been realised, it would take _well over a decade_ of interest to cover those losses.

#### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42251-operating-expenses-covered-4) Operating Expenses Covered

In my mind, the benefit of passing James’ proposal in some form now is that Karpatkey would be in a position to DCA out of ETH over the next 12-24 months or otherwise sell ETH if there is a spike in the price at any point.

#### [Heading link](https://discuss.ens.domains/t/endowment-initiation/15952\#p-42251-endowment-management-5) Endowment Management

The inflexibility of Karpatkey’s current strategy here is worrying.

At a bare minimum, I would expect an endowment manager to care about the price of ETH and have a clear strategy in place for disposing ETH, rather than market selling with no consideration of the price.

## post by Theth.eth on Jan 23, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/theth.eth/48/8420_2.png)](https://discuss.ens.domains/u/theth.eth)

[Theth.eth](https://discuss.ens.domains/u/theth.eth)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/7 "Post date")

Agree

" Endowment Management

The inflexibility of Karpatkey’s current strategy here is worrying.

At a bare minimum, I would expect an endowment manager to care about the price of ETH and have a clear strategy in place for disposing ETH, rather than market selling with no consideration of the price."

## post by nick.eth on Jan 24, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)](https://discuss.ens.domains/u/nick.eth)

[nick.eth](https://discuss.ens.domains/u/nick.eth)[Delegate](https://discuss.ens.domains/g/delegates)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/8 "Post date")

This is the hindsight fallacy, though; in December there was no way to know what the price would do in January, just like there is no way for us to know what it will do in February. I’m onboard with DCAing out of ETH, but we shouldn’t pretend we can time the market or predict which way ETH will move.

I do think an extended period (12-24 months) is excessive and exposes us to significant risk, though; if the ETH price plunges, both our income and our holdings will follow; if we sell more quickly but the price rises, we miss out on some upside, but our revenues are likely to be robust. Selling now is not about realising the maximum value of the ETH, it’s about minimising the chance of a catastrophic outcome.

## post by alisha.eth on Jan 24, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/alisha.eth/48/8743_2.png)](https://discuss.ens.domains/u/alisha.eth)

[alisha.eth](https://discuss.ens.domains/u/alisha.eth)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/9 "Post date")

It works in both directions — if the price of ETH plunges in the next three months, Karpatkey’s plan is to sell the ETH irrespective of the price, rather than waiting for the price to recover.

The example I used illustrates the point that getting the timing of a sale right is potentially more important than the yields we can expect to make from the endowment. If we shouldn’t care about the price of ETH at the time of sale, why should we care about the potential yields from an endowment strategy?

The sale of 10,000 ETH gives us breathing room within the endowment to pick the right time to convert additional ETH into USDC or to DCA out into USDC over time.

An endowment manager should not be market selling thousands of ETH, worth millions of dollars, without considering the price of ETH at the time of sale. I don’t feel that this is too much to ask. Risk reduction and sound treasury management practices are not mutually exclusive.

## post by garypalmerjr on Jan 24, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/garypalmerjr/48/949_2.png)](https://discuss.ens.domains/u/garypalmerjr)

[garypalmerjr](https://discuss.ens.domains/u/garypalmerjr)[Delegate](https://discuss.ens.domains/g/delegates)

1

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/10 "Post date")

This seems like a potential for a mess.

Why are we trusting centralized institutions for this much risk?

This is not decentralized; this is giving too much risk & ambiguity to a fund manager.

Why are we giving Karpatkey the entire treasury (minus 2-year runway)?

How does anyone think this is a good idea?

Why is the plan to sell 100% of the ENS DAO ETH?

I want us to hold ETH, not 100% centralized USDC!

Who will have these roles?

What is their governance?

How much will be added to this proposal after is passes?

All information is not included here, & we’re expected to just agree later?

Next steps?

Is there no way out of this?

I thought this was **not** guaranteed to happen, and that the vote was just an initial temperature check?

Seems like many with power are rushing to push this through–why the rush instead of just converting ETH to USDC, to address the runway concerns?

This does not seem like an exhaustive list of safeguards, for the all the potential risks that could be accounted for, in this situation, for this system setup.

\_\_

If we are worried about the price of ETH crashing, and not having the runway to fund ENS Labs,

then why don’t we simply sell the 10,000 ETH (as James proposed), and be safe with it?

Selling and loosing over 50% of the ENS DAO treasury seems dangerous & haphazard, (especially with all of the concerns rug pulls and fund-mixing, from other indirect-insolvent financial institutions).

The Karpatkey plan just gets more complicated and more confusing with each pass and review; we are moving in the wrong direction (for the stated/desire goals); while adding systemic risk to the best DAO in Web3.

Is Karpatkey and a treasury management firm a type of Attack Vector?

## post by elbagococina on Jan 24, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/elbagococina/48/8345_2.png)](https://discuss.ens.domains/u/elbagococina)

[elbagococina](https://discuss.ens.domains/u/elbagococina)[Delegate](https://discuss.ens.domains/g/delegates)

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/alisha.eth/24/8743_2.png)alisha.eth](https://discuss.ens.domains/t/endowment-initiation/15952 "Load parent post")

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/11 "Post date")

Hi Alisha!

This is our strategy:

- We don’t time the market or do trading based on price predictions.
- We’ll do DCA once we can ensure we have enough runway. Selling ETH asap is a risk management strategy.
- We will optimise the best price through small trades, spaced in time with a goal of slippage <0.2%

## post by nick.eth on Jan 24, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)](https://discuss.ens.domains/u/nick.eth)

[nick.eth](https://discuss.ens.domains/u/nick.eth)[Delegate](https://discuss.ens.domains/g/delegates)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/12 "Post date")

There is no way to time the market. Nobody has any idea what the ETH price will do next, and there’s no way to know when the price will rise or fall. DCAing is a good way to smooth out the price over a longer period, but trying to wait for “the right time” is simply engaging in speculation - something the DAO should not be doing.

None of this proposal requires trusting any centralised institutions.

The first endowment vote was in September, and the winner was selected in November. Nothing about this is rushed.

## post by santinomics.eth on Jan 24, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/santinomics.eth/48/7178_2.png)](https://discuss.ens.domains/u/santinomics.eth)

[santinomics.eth](https://discuss.ens.domains/u/santinomics.eth)

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/alisha.eth/24/8743_2.png)alisha.eth](https://discuss.ens.domains/t/endowment-initiation/15952 "Load parent post")

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/13 "Post date")


[... middle omitted — see footer ...]


The Harvester and Swapper roles, which automate rewards claiming and swapping tasks, are subsets of the Manager role. These roles will be managed by EOAs and will only be granted permissions that have been previously approved for the Manager role.

Any new permissions or roles that are deemed necessary will be formally requested and presented to the DAO via a forum post, which will include a rationale for the request. This will provide an opportunity for community members to ask questions or provide feedback. No actions will be taken without the approval of the DAO. In addition, a summary of any new roles and permissions that are approved and implemented will be shared in periodic reports to keep the community informed.

## post by garypalmerjr on Jan 25, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/garypalmerjr/48/949_2.png)](https://discuss.ens.domains/u/garypalmerjr)

[garypalmerjr](https://discuss.ens.domains/u/garypalmerjr)[Delegate](https://discuss.ens.domains/g/delegates)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/15 "Post date")

Questions:

1. Are their videos that detail how this technically works for the DAO?
2. Currently, is this same system being used by other DAOs, or is this new?
3. Which parts are new, for this implementation with the ENS DAO Endowment?

The system mechanics were not clear w/ confusion. I think a majority of votes did not want this, but it is happening.

Questions:

1. How much $ETH will be retained in the ENS DAOs Contracts?
2. How much $ETH will be retained as $ETH via/in this endowment proposal?

## post by santinomics.eth on Jan 25, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/santinomics.eth/48/7178_2.png)](https://discuss.ens.domains/u/santinomics.eth)

[santinomics.eth](https://discuss.ens.domains/u/santinomics.eth)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/16 "Post date")

I am quoting the answer from the post:

The DAO will retain 8,495 ETH according to market conditions at the time of submitting the post.

If the [proposal](https://discuss.ens.domains/t/draft-executable-sell-eth-into-usdc/15906) to sell ETH moves forward, the ETH would need to come from the controller as stated in the table above, as all the remaining ETH is expected to be transferred to the Endowment.

I am also quoting the original post with the answer:

Only the unearned portion will be kept as ETH.

## post by Zarathustra on Jan 25, 2023

[![](https://discuss.ens.domains/letter_avatar_proxy/v4/letter/z/898d66/48.png)](https://discuss.ens.domains/u/zarathustra)

[Zarathustra](https://discuss.ens.domains/u/zarathustra)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/17 "Post date")

Hi, [@garypalmerjr](https://discuss.ens.domains/u/garypalmerjr). I’m Karpatkey’s Tech Lead.

As of now we haven’t released any videos, but you can check out [this tutorial](https://zodiac.wiki/index.php/Roles_Modifier:_Operator_Tutorial) and [this thread](https://twitter.com/santinomics_/status/1613576303483162627?s=20&t=TecDKf567IWpvdbHAplWKg) which provide a description of how the setup works.

From a technical standpoint, you can check out [this](https://github.com/gnosis/zodiac-modifier-roles/blob/main/README.md).

Bear in mind that the use of the “new” SAFE provided by Karpatkey was agreed with the stewards only to facilitate a smoothier initiation of the Endowment by only having to transfer ETH as an action of the Tally executable proposal instead of the Roles Modifier deployment and its configuration through the assignment of the role and the application of the preset.

This system is already used in production by the Gnosis DAO, and has been adopted by the Balancer DAO as per [BIP-103](https://snapshot.org/#/balancer.eth/proposal/0xddc174b931a0d2e5e32276a3d0d7110367797dd24248f078d0f7876d0987c92f).

The “novelty” is the [Manager Role preset](https://github.com/gnosis/zodiac-modifier-roles/blob/mainnet-presets-progress/packages/sdk/src/presets/mainnet/deFiManageENS1.ts) designed to grant the (minimum) number of [permissions](https://docs.google.com/document/d/11xrliJIveXO6C6twYOrnGJ5QUW0Apr1LCcDY8hOfpuo/edit#heading=h.w1lggqyw11il) regarding target addresses, function signatures and their arguments needed for the execution of the outlined allocation strategy in a manner that by no means could jeopardize the ENS DAO’s custody of the funds.

## post by nick.eth on Jan 25, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)](https://discuss.ens.domains/u/nick.eth)

[nick.eth](https://discuss.ens.domains/u/nick.eth)[Delegate](https://discuss.ens.domains/g/delegates)

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/garypalmerjr/24/949_2.png)garypalmerjr](https://discuss.ens.domains/t/endowment-initiation/15952 "Load parent post")

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/18 "Post date")

Gary, many/most of your questions have already been answered in previous EPs, or in discussions that are publicly available here in the forum. Please take the time to read existing material before imposing on others’ time.

## post by alisha.eth on Jan 25, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/alisha.eth/48/8743_2.png)](https://discuss.ens.domains/u/alisha.eth)

[alisha.eth](https://discuss.ens.domains/u/alisha.eth)

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/19 "Post date")

What does this mean? How much runway is “enough”?

Saying that you don’t time the market doesn’t change the fact that you are choosing the strategy and you are choosing the time to sell. If the price of ETH doesn’t perform well in the immediate term, as sales are executed, I expect the endowment will be judged rather harshly. Claiming price blindness isn’t going to change that.

If this strategy goes ahead, the performance of the endowment will always be compared to the relative performance of ETH.

One of the benefits of getting ETH out of the treasury is that decisions can be made quickly, without having to wait for an executable proposal to pass. These benefits are being squandered.

If Karpatkey is uncomfortable making trading decisions, one solution might be to create a new polling environment on Snapshot and run a 24 hour poll each time Karpatkey plans to execute a sale. Delegates then have the opportunity to decide. If the poll is approved, Karpatkey would execute a sell.

I struggle to see how selling most of the ETH that has been generated by the protocol since 2019 on three random days at the start of 2023, with no consideration of price, lines up with the long term goals of the endowment.

The fact that ENS generates revenue in ETH is a blessing, not a burden.

The DAO doesn’t have any fixed costs that couldn’t be pared back if needed, apart from a stream to ENS Labs.

The proposal to sell 10,000 ETH addresses any immediate operational cost concerns.

I do not understand the alarmist rhetoric here. We want to create something that will last 100+ years, but need to act like there is an imminent threat of a cataclysmic event in the next few months?

We are in a bear market and have been for some time.

ETH revenue in dollar terms is still significantly greater than the DAO’s expenses.

The Ethereum Foundation conducts [large sells of ETH](https://www.trustnodes.com/2022/11/25/the-ethereum-foundation-sold-100000-eth) on a regular basis and they seem to have been able to time the market quite well. I wonder if we could reach out to the Ethereum Foundation to get an insight into their selling strategy?

Three sells at three prices over three months is not effective DCAing.

## post by SpikeWatanabe.eth on Jan 26, 2023

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/spikewatanabe.eth/48/537_2.png)](https://discuss.ens.domains/u/spikewatanabe.eth)

[SpikeWatanabe.eth](https://discuss.ens.domains/u/spikewatanabe.eth)[Delegate](https://discuss.ens.domains/g/delegates)

2

[Jan 2023](https://discuss.ens.domains/t/endowment-initiation/15952/20 "Post date")

**Past performance is not indicative of future performance**

However just to add a bit of colour to the discussion

Previous and very aggressive growth of price of ethereum was most likely influenced by two factors:

**1 - “helicopter” money** \- when governments were giving away a lot of money trying to “add some oil” to the system, a bit more liquidity = not so rough landing. More money in circulation, more people spend it on stuff which is not exactly essential for them, like cryptocurrencies. Average Joe may never buy any crypto in his life, but with some “free money” - Why not?

**2 - The fact that tons of people stayed at home.** To deal with cryptocurrencies you need to invest some time and effort - figure out how wallets work, how to handle exchanges and so on. Typically a lot of people don’t know how to do any of that, or can’t be bothered to find out even if they were interested a tiny bit in the past. Now you have all this time in the world, to sit around your flat and do various stuff, why not “do some cryptocurrencies”? Especially if your free time is financed with “free government money” (1)

Similarly during pandemic stock prices of companies engaged in video games production skyrocketed. A lot of people just had nothing else to do, but to play games, among other things of course.

_On top of that_

**3 - My hypothesis is that transition from PoW to PoS on Ethereum added additional pressure to price of Ethereum.** Mining of Eth was a perfect marketing tool, every single person out of there was home mining one way or the other. They were talking to each other, exchanging tips and hot news. This factor is gone now, so many retail investors just “turned off” from Eth ecosystem.

* * *

I’m perfectly on board with KK in a sense that not engaging in “market predictions” is one of the best practices out there, along with not engaging in other risky strategies. However there are plenty of factors to suggest that previous price cycle was hardly sustainable. It is certainly a conventional wisdom that cryptocurrency markets have huge growth potential due to // technology growth // increased adoption // argument that market is very small compared to gold and derivatives - and other similar logic. All that logic generally applies to what economists call “long term” performance, and while it may be true, economists also satirically assert that in the long run we are all dead.

UPDATE:

To put things in perspective, central banks assets

![cb assets](https://discuss.ens.domains/uploads/db9688/original/2X/c/c8b72b8a72d46d6d4e5169889ff74a055d47c24c.png)

In very simple terms, this is how much money they’ve created to tackle the pandemic. What’s going to happen next is that **they will slowly syphon out this excess liquidity from the system**, trying to keep inflation in check and not slow the economy. The question everyone should be asking - where is the money going to come from to fuel sudden growth of Eth price.

## Load more posts below

Invalid date

Invalid date

──────── [TRUNCATED] ────────
Showing 33,690 chars (head) + 11,162 chars (tail) of 47,710 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\discuss.ens.domains-1db316ce38.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\discuss.ens.domains-1db316ce38.md" offset=564 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────