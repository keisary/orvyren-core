# URL: https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173
# fetched: 2026-10-15T02:59:13.327595Z

[Skip to main content](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173#main-container)

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


# [\[EP 5.12\] Roles Modifier V2 Migration & Updates to Endowment Permissions](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173)

[🗳️ Meta-Governance](https://discuss.ens.domains/c/meta-governance/28) [Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64)

You have selected **0** posts.

[select all](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173)

[cancel selecting](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173)

2.2k
views
24
likes
39
links
6
users


[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/estmcmxci/48/14020_2.png)4](https://discuss.ens.domains/u/estmcmxci "estmcmxci")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/kpk/48/13441_2.png)3](https://discuss.ens.domains/u/kpk "kpk")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)2](https://discuss.ens.domains/u/nick.eth "nick.eth")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/snowdot/48/10155_2.png)2](https://discuss.ens.domains/u/snowdot "snowdot")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/5pence.eth/48/10424_2.png)2](https://discuss.ens.domains/u/5pence.eth "5pence.eth")

read
8
min


[May 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/1 "Jump to the first post")

2 / 14


May 2024


[Aug 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/14)

## post by kpk on May 6, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/kpk/48/13441_2.png)](https://discuss.ens.domains/u/kpk)

[kpk](https://discuss.ens.domains/u/kpk)

2

[May 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173 "Post date")

# [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53041-abstract-1) Abstract

This proposal aims to roll out an updated version of the Zodiac Roles Modifier module. The new version improves usability and transparency of treasury management operations. Upon approval, the Roles Modifier v2 module will be activated.

Furthermore, this proposal requests authorization from the DAO to revise the permissions policy. A notable change includes enabling swapping actions on CoW Swap while the other permissions primarily focus on eliminating obsolete actions and protocols, and refining parameters within the existing permissions.

# [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53041-roles-v2-migration-2) Roles v2 Migration

## [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53041-motivation-3) Motivation

As [previously stated](https://discuss.ens.domains/t/endowment-initiation/15952#a-list-of-zodiac-roles-modifier-permissions-for-the-manager-role-9), the Zodiac Roles Modifier facilitates karpatkey’s proxy management of the Endowment by ensuring that only pre-approved transactions, defined by the permissions policy voted on by the DAO, can be executed. In collaboration with karpatkey, the Gnosis Guild team has significantly upgraded the Zodiac Roles Modifier module and the Zodiac Roles app. These enhancements have resulted in a more powerful and robust on-chain permissions infrastructure with the following improvements:

- **Introduction of Allowances**: Implementation of spending limits within permissions.
- **Enhanced Call Data Scoping Toolset**: This toolset considerably broadens the range of functions that can have permissions set, increasing flexibility.
- **Advanced Logical Conditions**: Allows for the creation of complex permissions structures to accommodate sophisticated operational needs.
- **Compatibility with [DeFi Kit](https://kit.karpatkey.com/)**: This feature integrates with karpatkey’s permissions policy building module, facilitating the straightforward crafting of protocol actions.
- **Improved Visualisation and User Interface**: the new [Zodiac Roles app UI](https://roles.gnosisguild.org/) not only displays permissions clearly but also provides a user-friendly interface to compare changes in each policy update, enhancing transparency and simplifying audits.

For more detailed information, please refer to the following resources:

- **Documentation**: [The Zodiac Roles Modifier](https://docs.roles.gnosisguild.org/)
- **Articles**: [Evolving Smart Accounts with Onchain Permissions](https://gnosisguild.mirror.xyz/oQcy_c62huwNkFS0cMIxXwQzrfG0ESQax8EBc_tWwwk), [Permissions as code](https://engineering.gnosisguild.org/posts/permissions-as-code)

## [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53041-contract-audits-4) Contract Audits

The Zodiac Roles Modifier v2 contract has been rigorously audited by G0 Group, the internal auditing team of Gnosis DAO, and by [Omniscia](https://omniscia.io/). The detailed audit reports are available for review [here](https://github.com/gnosisguild/zodiac-modifier-roles/tree/main/packages/evm/docs).

# [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53041-changes-to-the-permissions-policy-5) Changes to the Permissions Policy

This proposal outlines the following modifications to the permissions policy:

1. **Token Arrays for Swapping**:

1. Considering the tokens involved in the existing permissions, we have updated the token arrays to ensure they can be seamlessly swapped across the various whitelisted protocols and aggregators.
2. **Token IN Allowlist**: \[CRV, DAI, USDT, BAL, AURA, CVX, ETHx, COMP, rETH, SWISE, wstETH, LDO, WETH, ankrETH, USDC, stETH\].
3. **Token OUT Allowlist**: \[DAI, USDT, USDC, rETH, wstETH, WETH, stETH\].
4. The above arrays are to be utilised for swapping on CoW Swap, with equivalent lists replicated for Uniswap v3 and Balancer.
2. **Introduction of CoW Swap** ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#right-0x23da9ade38e4477b23770ded512fd37b12381fab)):


5\. Addition of a **CoW Swap Order signer** to enable gas-minimised and MEV-protected swaps. This includes an extensive set of aggregated exchange routes, improving the efficiency and effectiveness of required swaps.


6\. Tokens will be swapped on CoW Swap according to the token IN/OUT allowlists mentioned above.
3. **Deprecations and Removals**:


7\. **Uniswap v2 Swaps** ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#left-0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45-0x472b43f3)): Removed due to insufficient liquidity in V2 pools.


8\. **Stakewise v2**: Deprecated functions related to deposit ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#left-0xc874b064f465bdd6411d45734b56fac750cda29a)) and claim ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#left-0xa3f21010e8b9a3930996c8849df38f9ca3647c20)) functions in light of the recent launch of Stakewise v3. Consequently, permitted actions related to Stakewise v2’s sETH2-ETH Uniswap pool are also removed ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#left-0xc36442b4a4522e871399cd717abdd847ab11fe88)).


9\. **Compound v2** ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#left-0x39aa39c021dfbae8fac545936693ac917d5e7563)): Discontinued all actions targeting v2 contracts and v2 cTokens (cUSDC and cDAI) due to the ongoing transition of the protocol to its v3.


10\. **Revocation of Existing/Obsolete Allowances:** All existing and outdated allowances previously set by the Endowment are revoked (set to zero). The ability to call the corresponding approve functions is included in the newly proposed policy. Accordingly, the payload contains a bundle of transactions to revoke these allowances.
4. **Updates**:


11\. **Uniswap v3** ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#right-0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45-0x04e45aaf)) **and Balancer** ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#right-0xba12222222228d8ba445958a75a0704d566bf2c8)): Adjusted to allow the mentioned token IN/OUT allowlists.


12\. **Curve Pools**: Addition of stETH-ng (factory) pool ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/rMNui3Yp9LlBScVLFjY9cWkk4QGYoIVkkYxURs16ys?annotations=false#right-0x21e27a5e5513d6e65c4f830167390997aa84843a)) and removal of cUSDC + cDAI pool ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/rMNui3Yp9LlBScVLFjY9cWkk4QGYoIVkkYxURs16ys?annotations=false#left-0xa2b47e3d5c44877cca798226b7b8118f9bfb7a56); Compound v2 tokens).


13\. **Curve ZAP Deposit Contract** ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/rMNui3Yp9LlBScVLFjY9cWkk4QGYoIVkkYxURs16ys?annotations=false#right-0x56c526b0159a258887e0d79ec3a80dfb940d0cd7)): Introduced to allow depositing and staking of LP tokens in a single step.


14\. **Convex Staking** ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#right-0x6b27d7bc63f1999d14ff9ba900069ee516669ee8)): Added the CVX/stETH Rewards contract.


15\. **Lido Withdrawals** ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#right-0x889edc2edab5f40e902b864ad4d7ade8e412f9b1)): Enhanced to include new withdrawal methods using permits for both wstETH and stETH; methods include `requestWithdrawalsWstETHWithPermit` and `requestWithdrawalsWithPermit`.


16\. **Spark Rewards Claim** ( [diff](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false#right-0x4370d3b6c9588e02ce9d22e684387859c7ff5b34)): Added functionality to claim wstETH rewards in Spark.

# [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53041-audit-considerations-6) Audit Considerations

We highly value the community’s involvement in reviewing and providing feedback on this proposal. We encourage members with the necessary technical expertise to examine the content carefully (including this [payload](https://gist.github.com/santinomics/773117b729152f31a121045f4ba26b5b)) and share their insights with us.

For effective testing of the permissions policy configuration, we have utilised a [Testing Avatar Safe](https://app.safe.global/balances?safe=eth:0xC01318baB7ee1f5ba734172bF7718b5DC6Ec90E1). This safe mirrors the current state of the [permissions policy v4](https://docs.google.com/document/d/1Ker_TkBJV0xmQ9Li9HB-vtdlpx1vEeVEQwpIH6WoK0o) granted by the Endowment to the Manager SAFE operated by karpatkey. The enhancements in the Zodiac Roles app interface now allow for a clear visualisation of all existing permissions, accessible [here](https://roles.gnosisguild.org/eth:0xbd1099dfd3c11b65fb4bb19a350da2f5b61efb0d/roles/ENS-MANAGER-V1).

The updated interface also simplifies the process of identifying [changes](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false) by displaying the current permissions policy on the left side and the newly proposed policy on the right side. To further aid in the adoption and understanding of these tools for audit purposes, we have detailed the proposed changes in [version 5 documentation](https://docs.google.com/document/d/1KU4a7s-AxAAAPJxd8vexn7kCl8hsr3-c7VIDfEPHbKc/edit), following our standard Policy Update Request (PUR) format.

# [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53041-additional-considerations-7) Additional considerations

## [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53041-roles-modifier-v1-and-enabling-of-v2-8) Roles Modifier v1 and Enabling of v2

The existing Roles Modifier v1 module will remain active to ensure a smooth transition and prevent any unexpected disruptions in operational execution. Ownership of the deployed [Roles Modifier v2 module](https://etherscan.io/address/0x703806E61847984346d2D7DDd853049627e50A40), equipped with the new proposed permissions policy, has been [transferred](https://etherscan.io/tx/0x78c69c7ad0c5f430d97ec5c3bac5cb649d831a756b3d4c5b09b45152427ae8f4) to the Endowment’s Avatar Safe. These permissions are displayed [here](https://roles.gnosisguild.org/eth:0x703806e61847984346d2d7ddd853049627e50a40/roles/MANAGER) and match those shown on the comparison interface [here](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/rMNui3Yp9LlBScVLFjY9cWkk4QGYoIVkkYxURs16ys?annotations=false). The payload will only activate this module, marking the first phase of the migration process. A subsequent policy update proposal will seek to disable the v1 module.

## [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53041-policy-visualisation-in-terms-of-defi-kit-actions-9) Policy Visualisation in Terms of DeFi Kit Actions

The “show annotations” button, located at the top-right [here](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/rMNui3Yp9LlBScVLFjY9cWkk4QGYoIVkkYxURs16ys?annotations=false), provides a visualisation of the proposed permissions policy expressed through the DeFi Kit Protocol Actions. This feature offers a more abstract and simplified description of the policy, enhancing understanding and accessibility.

- [ENS DAO Newsletter #63 — 06/18/24](https://discuss.ens.domains/t/ens-dao-newsletter-63-06-18-24/19315)
- [ENS DAO Newsletter #61 — 05/21/24](https://discuss.ens.domains/t/ens-dao-newsletter-61-05-21-24/19208)
- [ENS DAO Newsletter #64 — 07/02/24](https://discuss.ens.domains/t/ens-dao-newsletter-64-07-02-24/19354)
- [\[EP 6.2\] \[Executable\] Endowment expansion (3rd tranche)](https://discuss.ens.domains/t/ep-6-2-executable-endowment-expansion-3rd-tranche/19851)
- [ENS DAO Newsletter #60 — 05/07/2024](https://discuss.ens.domains/t/ens-dao-newsletter-60-05-07-2024/19175)
- 4 more

2.2k
views
24
likes
39
links
6
users


[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/estmcmxci/48/14020_2.png)4](https://discuss.ens.domains/u/estmcmxci "estmcmxci")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/kpk/48/13441_2.png)3](https://discuss.ens.domains/u/kpk "kpk")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)2](https://discuss.ens.domains/u/nick.eth "nick.eth")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/snowdot/48/10155_2.png)2](https://discuss.ens.domains/u/snowdot "snowdot")

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/5pence.eth/48/10424_2.png)2](https://discuss.ens.domains/u/5pence.eth "5pence.eth")

read
8
min


## post by nick.eth on May 7, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)](https://discuss.ens.domains/u/nick.eth)

[nick.eth](https://discuss.ens.domains/u/nick.eth)[Delegate](https://discuss.ens.domains/g/delegates)

[May 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/2 "Post date")

Thanks Karpatkey! A step-by-step “how to audit this” would be really useful given the new improvements to the roles modifier.

## post by kpk on May 8, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/kpk/48/13441_2.png)](https://discuss.ens.domains/u/kpk)

[kpk](https://discuss.ens.domains/u/kpk)

[May 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/3 "Post date")

# [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53076-auditing-steps-1) Auditing Steps

## [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53076-current-permissions-policy-2) Current Permissions Policy

- [Link 1](https://docs.google.com/document/d/1Ker_TkBJV0xmQ9Li9HB-vtdlpx1vEeVEQwpIH6WoK0o/edit): Current Permissions Policy v4 (PP v4).
- [Link 2](https://app.safe.global/apps/open?safe=eth:0x4F2083f5fBede34C2714aFfb3105539775f7FE64&appUrl=https%3A%2F%2Fzodiac.gnosisguild.org%2F): PP v4 currently deployed in the Roles v1 module as displayed in the Zodiac app (navigate to “edit roles”, toggle the roles, review target contracts).
- [Link 3](https://roles.gnosisguild.org/eth:0xbd1099dfd3c11b65fb4bb19a350da2f5b61efb0d/roles/ENS-MANAGER-V1): Same policy as Link 2, but deployed in a Roles v2 module.

First auditing step: Verify that the permissions in Link 3 match those in Link 2.

## [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53076-comparison-of-current-permissions-policy-vs-new-proposed-policy-3) Comparison of Current Permissions Policy vs New Proposed Policy

- [Link 4](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false): Comparison of the current policy (left) vs. the new proposed policy (right).

Second auditing step:

- Assess the newly added permissions in the proposed policy (highlighted in green on the right).
- Review the revoked permissions from the old policy (highlighted in red on the left).
- Examine the updated or modified permissions (indicated in blue on both sides).

Detailed descriptions of the changes in the permissions policy are available [here](https://discuss.ens.domains/t/ep-5-x-roles-modifier-v2-migration-updates-to-endowment-permissions/19173#changes-to-the-permissions-policy-5).

## [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53076-enabling-roles-v2-by-the-endowment-4) Enabling Roles v2 by the Endowment

- Ownership of the [Roles Modifier v2 module](https://etherscan.io/address/0x703806E61847984346d2D7DDd853049627e50A40), equipped with the new proposed permissions policy, has been [transferred](https://etherscan.io/tx/0x78c69c7ad0c5f430d97ec5c3bac5cb649d831a756b3d4c5b09b45152427ae8f4) to the Endowment.
- [Link 5](https://roles.gnosisguild.org/eth:0x703806e61847984346d2d7ddd853049627e50a40/roles/MANAGER): The new permissions policy deployed in the Roles v2 module.

Third auditing step: Verify that the new proposed policy is consistent with the policy in Roles v1 (as per Link 4, right side) and with the policy in Roles v2 (Link 5).

# [Heading link](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173\#p-53076-future-audits-5) Future Audits:

- Future audits will require only the “Current Permissions Policy vs. New Proposed Policy” step.
- Changes in policies will be assessed by identifying which [DeFi Kit actions](https://kit.karpatkey.com/learn/protocols) are added or removed, streamlining the process by bypassing the analysis of individual permissions.

- [Karpatkey 2024 Review for the ENS Endowment](https://discuss.ens.domains/t/karpatkey-2024-review-for-the-ens-endowment/20095)
- [Karpatkey H1 2024 Review for the ENS Endowment](https://discuss.ens.domains/t/karpatkey-h1-2024-review-for-the-ens-endowment/19394)

25 days later


## post by estmcmxci on Jun 2, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/estmcmxci/48/14020_2.png)](https://discuss.ens.domains/u/estmcmxci)

[estmcmxci](https://discuss.ens.domains/u/estmcmxci)[Delegate](https://discuss.ens.domains/g/delegates)

[Jun 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/4 "Post date")

Hi Team Karpatkey,

Thank you for the detailed auditing steps. I have taken the liberty of auditing the permissions policy updates and have prepared detailed commentary [here](https://hackmd.io/@estmcmxci/audit-karpatkey-purv5). For anyone reviewing the PUR as well, I hope that the comments I prepared save time.

I have a few questions:

1. After verifying that the existing permissions in the v2 module match the permissions listed in the v1 module (according to PP v4) as instructed in the first auditing step, I noticed that the target address listed as [0xc874…](https://roles.gnosisguild.org/eth:0xbd1099dfd3c11b65fb4bb19a350da2f5b61efb0d/roles/ENS-MANAGER-V1#0xc874b064f465bdd6411d45734b56fac750cda29a) describes _‘function not found in ABI’_ and _‘no condition set_’ in either module version. In [PP v4](https://docs.google.com/document/d/1KU4a7s-AxAAAPJxd8vexn7kCl8hsr3-c7VIDfEPHbKc/edit), the signature for this target address is described as _‘stake()’_ and is listed as revoked in [PP v5](https://docs.google.com/document/d/1KU4a7s-AxAAAPJxd8vexn7kCl8hsr3-c7VIDfEPHbKc/edit). Could you help reconcile this discrepancy?

2. While performing the third auditing step, I found that several tokens had a difference in the number of parameters listed in either module. For example, the wstETH token with target address [0x7f39…](https://roles.gnosisguild.org/eth:0x703806e61847984346d2d7ddd853049627e50a40/roles/MANAGER#0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0) has 2 parameters listed in the v2 module, whereas in the v1 module, there are three additional parameters listed. This discrepancy occurs several more times. Could you shed some light on why there might be a difference in the number of parameters listed?


—

Thanks again for all your work! For anyone interested in the ENS Endowment, its initialization, and how this proposal enhances its administration, [check out this ELI5 article I wrote](https://mirror.xyz/estmcmxci.eth/auGEzmC25xL1fa25-XmfLAlEAozWoMXEUslNtlrBqpU).

## post by kpk on Jun 4, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/kpk/48/13441_2.png)](https://discuss.ens.domains/u/kpk)

[kpk](https://discuss.ens.domains/u/kpk)

[Jun 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/5 "Post date")

First and foremost; thank you very much for the thorough auditing, [@estmcmxci](https://discuss.ens.domains/u/estmcmxci).

We greatly appreciate the time and effort you put into examining the new version of our treasury management framework. We believe that both internal and external reviews of this module are essential, as it is the foundation for us to execute on behalf of the ENS Endowment properly and securely.

Our responses to your first auditing step are as follows:

- [0xc874b0…da29](https://etherscan.io/address/0xc874b064f465bdd6411d45734b56fac750cda29a) is an old Stakewise contract.


Stakewise deprecated the possibility of staking ETH in exchange for sETH2, which is why the function is no longer part of the contract’s ABI. In PP v5, we removed all Stakewise v2 permissions, which is why it is listed as revoked.

- [0x5550d…747d](https://etherscan.io/address/0x5550d13389bb70f45fcef58f19f6b6e87f6e747d) is an old Sushiswap route processing contract.


This permission had been removed in the last PUR update but ended up being added in the payload, which was subsequently [fixed](https://github.com/gnosisguild/zodiac-modifier-roles-v1/commit/64bebc23c66c9ed7137a7e8d9abce3575351af9b) on November 3rd.

- [0x5c0f2…0b1c](https://etherscan.io/address/0x5c0f23a5c1be65fa710d385814a7fd1bda480b1c) is Balancer’s wstETH-WETH gauge.


It appears both in the [v1](https://app.safe.global/apps/open?safe=eth:0x4F2083f5fBede34C2714aFfb3105539775f7FE64&appUrl=https%3A%2F%2Fzodiac.gnosisguild.org%2F) (“Edit roles” => “Role #1” =\> “Ctrl+F: 0x5c0f “) and [v2 module](https://roles.gnosisguild.org/eth:0xbd1099dfd3c11b65fb4bb19a350da2f5b61efb0d/roles/ENS-MANAGER-V1#0x5c0f23a5c1be65fa710d385814a7fd1bda480b1c) (as stated it should be on the first auditing step).


Regarding your second point, and third auditing step:

All of these functions are approval signatures whitelisting different protocols and exchanges we need to interact with. The EVM word has a length of 32 bytes, so to complete the word, addresses are padded with leading zeros. The new version of the App removes these leading zeros and converts hexadecimal values to be more human-readable.

For example;

The ‘0x095ea7b3’ signature you mention in the **spWETH** token contract is the ‘Approve’ function with an allowlisted input:’parameter\[0\]: 0x000000000000000000000000bd7d6a9ad7865463de44b05f04559f65e3b11704’.

Which can also be formatted as: ‘Spender: 0xBD7D6a9ad7865463DE44B05F04559f65e3B11704’, which is the [Spark.fi](http://spark.fi/) deployer.

For the other tokens you flagged, and their seemingly missing spenders; the [new permissions policy](https://roles.gnosisguild.org/eth:0x703806e61847984346d2d7ddd853049627e50a40/roles/MANAGER) deployed in the Roles v2 module has some of the approved addresses under actions tagged “DeFi kit by karpatkey”. These actions are useful for the [DeFi kit](https://kit.karpatkey.com/) we are building.

To make the third auditing step less labor-intensive, we added a “Hide annotations” toggle (top right-hand side) that removes the actions and aggregates all approved spenders in the same format as the [new proposed policy](https://roles.gnosisguild.org/eth:0xBd1099dFD3c11b65FB4BB19A350da2f5B61Efb0d/roles/ENS-MANAGER-V1/diff/C0zUV4NtNErufEpbpNc2S55F2oiAGw8aKE2jYwWjLg?annotations=false) (right).

## post by 5pence.eth on Jun 4, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/5pence.eth/48/10424_2.png)](https://discuss.ens.domains/u/5pence.eth)

[5pence.eth](https://discuss.ens.domains/u/5pence.eth)

[Jun 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/6 "Post date")

Thanks [@estmcmxci](https://discuss.ens.domains/u/estmcmxci)

And thanks [@santinomics.eth](https://discuss.ens.domains/u/santinomics.eth) and [@kpk](https://discuss.ens.domains/u/kpk),

Your partnership and support continue to exceed expectations. Thank you for always going above and beyond in your service.

We’d like to help you time this proposal with a couple of other executable proposals that we’re suggesting be posted around the middle of the month - we’re softly targeting around June 19th.

27 days later


## post by estmcmxci on Jul 2, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/estmcmxci/48/14020_2.png)](https://discuss.ens.domains/u/estmcmxci)

[estmcmxci](https://discuss.ens.domains/u/estmcmxci)[Delegate](https://discuss.ens.domains/g/delegates)

[Jul 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/7 "Post date")

The executable version of this proposal is now live onchain. Vote here: [Tally \| ENS \| \[EP 5.12\] Roles Modifier V2 Migration & Updates to Endowment Permissions](https://www.tally.xyz/gov/ens/proposal/107992041043258996427224563090014372885335179099580585497266204203463156791290)

## post by lefterisjp on Jul 5, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/lefterisjp/48/732_2.png)](https://discuss.ens.domains/u/lefterisjp)

[lefterisjp](https://discuss.ens.domains/u/lefterisjp)[Delegate](https://discuss.ens.domains/g/delegates)

[Jul 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/8 "Post date")

I had a look at the details of the change. It looks quite interesting and is probably fine but I have not had time to dig dip into it.

I asked around and was told that some others including [@estmcmxci](https://discuss.ens.domains/u/estmcmxci), [@nick.eth](https://discuss.ens.domains/u/nick.eth) and [@netto.eth](https://discuss.ens.domains/u/netto.eth) had had audited it. After talking with them it sounded like everyone sort of looked at it but no thorough audit was made. Or at least that’s how it sounded to me.

I then approached the people of Karpatkey who proposed it and was told they had very carefully audited and they even offered to guide me through it via a call. But since the vote ends in less than 2 days and I have no free time I could not make it.

All the above lead me to vote abstain since I can’t confidently say if it’s a safe change or not.

## post by snowdot on Jul 8, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/snowdot/48/10155_2.png)](https://discuss.ens.domains/u/snowdot)

[snowdot](https://discuss.ens.domains/u/snowdot)[Delegate](https://discuss.ens.domains/g/delegates)

1

[Jul 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/9 "Post date")

The results are in for the **\[EP 5.12\] Roles Modifier V2 Migration & Updates to Endowment Permissions** proposal!

See how the community voted and view the detailed analytics here:

⬡ [\# \[EP 5.12\] Roles Modifier V2 Migration & Updates to Endowment Permissions \| Dhive](https://dhive.io/proposal/640)

10 days later


## post by snowdot on Jul 18, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/snowdot/48/10155_2.png)](https://discuss.ens.domains/u/snowdot)

[snowdot](https://discuss.ens.domains/u/snowdot)[Delegate](https://discuss.ens.domains/g/delegates)

1

[Jul 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/10 "Post date")

During the last Meta-Gov call, [@estmcmxci](https://discuss.ens.domains/u/estmcmxci) brought up a very good point related to the interpretation of the criteria needed to be fulfilled in order to establish if an on-chain proposal has passed or failed.

I will use this proposal as a case study to ensure I fully understood the explanation during the call and apply this method to check past and future on-chain proposals.

In the [documentation](https://docs.ens.domains/dao/proposals/submit), we have the following mention:

> 1. **[Executable Proposal](https://docs.ens.domains/content/dao/governance/executable-proposal-template.md):** This is a proposal for a series of smart contract operations to be executed by accounts the DAO controls. These can include transfers of tokens as well as arbitrary smart contract calls. Examples of this include allocating funding to a workstream multisig wallet, or upgrading an ENS core contract. Executable proposals have a quorum requirement of 1% and require a minimum approval of 50% to pass.

So there are two requirements that need to be met for an on-chain proposal to pass:

**1\. quorum requirement of 1%**

In the [smart contract](https://etherscan.io/address/0x323A76393544d5ecca80cd6ef2A560C6a395b7E3#readContract), the counting mode is set to `support=bravo&quorum=for,abstain` which means that we’re counting the total number of _for votes_ plus _abstain votes_ to establish if the quorum is met.

In this example, the quorum was reached:

666,376 _for votes_ \+ 709,506 _abstain votes_ \> 0.01 \* 100,000,000 _total supply_

=\> **1,375,882** _votes counted_ \> **1,000,000** _quorum threshold_![:white_check_mark:](https://discuss.ens.domains/images/emoji/twitter/white_check_mark.png?v=12)

So far, everything is clear and anyone can check this information directly in the contract.

**2\. minimum approval of 50%**

Here is where this requirement is subject to interpretation as it’s not specified exactly how the 50% should be calculated, nor can we find this information in the contract.

Although the result of _for votes_ is 666,376 _for votes_ / 1,376,526 _total votes_ \\* 100 = **48.41%**, the 50% requirement should be interpreted and calculated solely in relation to the total of _for votes_ plus _against votes_, as follows:

666,376 _for votes_ / (666,376 _for votes_ \+ 643 _against votes_) \\* 100 = 99.90%

=\> **99.90%** approval > **50%** minimum approval ![:white_check_mark:](https://discuss.ens.domains/images/emoji/twitter/white_check_mark.png?v=12)

Could you please confirm if my understanding and method of calculation are correct? Also, is it safe to apply the same method for past and future on-chain proposals to check whether or not a proposal passed?

Thank you very much!

## post by nick.eth on Jul 19, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/nick.eth/48/712_2.png)](https://discuss.ens.domains/u/nick.eth)

[nick.eth](https://discuss.ens.domains/u/nick.eth)[Delegate](https://discuss.ens.domains/g/delegates)

[Jul 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/11 "Post date")

That sounds correct to me. It would make no sense to count approval as `for / total`, because that would effectively make votes to abstain into votes against.

## post by estmcmxci on Jul 19, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/estmcmxci/48/14020_2.png)](https://discuss.ens.domains/u/estmcmxci)

[estmcmxci](https://discuss.ens.domains/u/estmcmxci)[Delegate](https://discuss.ens.domains/g/delegates)

[Jul 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/12 "Post date")

Thanks for pointing this out. Would it make sense to explicitly specify in the Governance Documentation that the 50% minimum approval is defined as the total of _for_ votes plus _against_ votes?

As [@netto.eth](https://discuss.ens.domains/u/netto.eth) originally pointed out, the Tally UI had incorrectly shown the proposal as defeated. Illustrating this example in the documentation could help delegates better understand the nuance of how minimum approval for an onchain vote is calculated.

## post by 5pence.eth on Jul 19, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/5pence.eth/48/10424_2.png)](https://discuss.ens.domains/u/5pence.eth)

[5pence.eth](https://discuss.ens.domains/u/5pence.eth)

[Jul 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/13 "Post date")

Hey [@snowdot](https://discuss.ens.domains/u/snowdot)! ![:grin:](https://discuss.ens.domains/images/emoji/twitter/grin.png?v=12) Thanks for asking for clarification on this. Yes, your interpretation is correct. That is how the DAO’s governor contract calculates the success or failure of the proposal. As Nick.eth mentioned, the 50% applying to Yes/No votes is the logical interpretation as well (when compared with others).

The language used to describe this in the documentation could be more explicit to help avoid misunderstanding. As [@estmcmxci](https://discuss.ens.domains/u/estmcmxci) alluded to, we are planning to propose some alternative or additional language in the near future that explains this more clearly.

1 month later


## post by estmcmxci on Aug 25, 2024

[![](https://discuss.ens.domains/user_avatar/discuss.ens.domains/estmcmxci/48/14020_2.png)](https://discuss.ens.domains/u/estmcmxci)

[estmcmxci](https://discuss.ens.domains/u/estmcmxci)[Delegate](https://discuss.ens.domains/g/delegates)

[Aug 2024](https://discuss.ens.domains/t/ep-5-12-roles-modifier-v2-migration-updates-to-endowment-permissions/19173/14 "Post date")

Hi there! ICYMI, ThirdGuard is now providing audit reports. The latest one for [PUR #4](https://www.tally.xyz/gov/ens/proposal/62537345451524095629071359388092434511638926463658570104856324869910407296726) can be found [here](https://github.com/ThirdGuard/roles-policy-audits/blob/main/ENS/ens-policy-audit-v2-21st-Aug-2024.pdf). I tried my best to audit on my own, but it’s a bit over my head ![:sweat_smile:](https://discuss.ens.domains/images/emoji/twitter/sweat_smile.png?v=12). I used the audit report as a sort of walkthrough to help me cross-reference permissions updates.

Reply

### New & Unread Topics

| Topic | Replies | Views | Activity |
| --- | --- | --- | --- |
| [\[EP 6.38\] \[Executable\] Endowment permissions to karpatkey - Update #8](https://discuss.ens.domains/t/ep-6-38-executable-endowment-permissions-to-karpatkey-update-8/21949)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [3](https://discuss.ens.domains/t/ep-6-38-executable-endowment-permissions-to-karpatkey-update-8/21949/1) | 133 | [Mar 19](https://discuss.ens.domains/t/ep-6-38-executable-endowment-permissions-to-karpatkey-update-8/21949/4) |
| [Update on the Endowment Fee Structure (Metagov + kpk)](https://discuss.ens.domains/t/update-on-the-endowment-fee-structure-metagov-kpk/21684)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [1](https://discuss.ens.domains/t/update-on-the-endowment-fee-structure-metagov-kpk/21684/1) | 336 | [Dec 2025](https://discuss.ens.domains/t/update-on-the-endowment-fee-structure-metagov-kpk/21684/2) |
| [Kpk 2025 Review for the ENS Endowment](https://discuss.ens.domains/t/kpk-2025-review-for-the-ens-endowment/21829)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [0](https://discuss.ens.domains/t/kpk-2025-review-for-the-ens-endowment/21829/1) | 224 | [Jan 20](https://discuss.ens.domains/t/kpk-2025-review-for-the-ens-endowment/21829/1) |
| [\[Executable\] Treasury Flow Automation](https://discuss.ens.domains/t/executable-treasury-flow-automation/21923)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [22](https://discuss.ens.domains/t/executable-treasury-flow-automation/21923/1) | 760 | [Jun 24](https://discuss.ens.domains/t/executable-treasury-flow-automation/21923/23) |
| [Security Update: Zodiac Roles Modifier v2 and Delay Modifier v1.1.0](https://discuss.ens.domains/t/security-update-zodiac-roles-modifier-v2-and-delay-modifier-v1-1-0/22161)<br>[Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) | [0](https://discuss.ens.domains/t/security-update-zodiac-roles-modifier-v2-and-delay-modifier-v1-1-0/22161/1) | 91 | [Jun 4](https://discuss.ens.domains/t/security-update-zodiac-roles-modifier-v2-and-delay-modifier-v1-1-0/22161/1) |

Topic list, column headers with buttons are sortable.

### Want to read more? Browse other topics in [Treasury Management](https://discuss.ens.domains/c/meta-governance/treasury-management/64) or [view latest topics](https://discuss.ens.domains/latest).

[Powered by Discourse](https://discourse.org/powered-by)

Invalid date

Invalid date