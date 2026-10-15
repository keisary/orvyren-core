URL: https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580/1
TITLE: rsETH Incident Report (April 20, 2026)

# rsETH Incident Report (April 20, 2026)
URL: https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580/1

# rsETH Incident Report (April 20, 2026)

URL: https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580
Category: Governance
Created: April 20, 2026, 8:12pm UTC
Posts on this page: 1
Showing post: 1

Author: @LlamaRisk
Post date: April 20, 2026, 8:12pm UTC

# rsETH Incident Report (April 20, 2026)

This report was co-authored by Aave service providers acting within their respective mandates and reflects the best available and verified information at the time of publication. We would also like to acknowledge and thank user banteg for their feedback on the exploit details.

## 1. Background

On 2026-04-18 at 17:35 UTC (Ethereum block 24,908,285), an attacker exploited Kelpâs LayerZero V2 Unichain to Ethereum rsETH route, which was configured as a 1-of-1 DVN. A forged inbound packet from Unichain (srcEid 30320) to Ethereum was verified by a single DVN attestation with no corresponding source-side burn. This released 116,500 rsETH from the Ethereum-side RSETH_OFTAdapter (0x85d456b2â¦98ef3) to the attacker.

Within minutes, the attacker fanned out the 116,500 rsETH from a single intake wallet across 7 branch addresses. From there, the branches followed divergent paths: some supplied rsETH as collateral on Aave V3 on Ethereum, some bridged funds to Arbitrum and opened Aave positions on that chain, and others were routed through different venues. Overall, 7 addresses of the attacker currently have active rsETH-backed loans, with health factors that settled around 1.01 to 1.03.

### How the exploit broke the bridge invariant

Kelp rsETH uses a LayerZero lock-and-mint bridge for cross-chain transfers. On Ethereum, rsETH is locked in the OFT adapter; on each remote chain, a corresponding amount of rsETH IOUs is minted. The invariant that should always hold is:

> rsETH locked in Ethereum adapter â¥ total rsETH minted across all remote chains

The Unichain â Ethereum route was configured as a 1-of-1 DVN path with no optional verifiers. A structurally normal-looking LayerZero packet (nonce 308) was PayloadVerified, committed, and delivered on Ethereum, releasing 116,500 rsETH from the adapter, without any corresponding burn or nonce advance on the Unichain source endpoint. The Unichain outbound nonce remained at 307 while Ethereum accepted nonce 308.

The adapter balance dropped from 116,723 rsETH (one block before the exploit) to 223 rsETH immediately after. An inbound packet (nonce 309, for an additional 40,000 rsETH) was also verified by the same single DVN, but its execution reverted as Kelp had already frozen the recipient address, withdrawing 40,373 rsETH from the adapter after initiating the FrozenFundsRecover. As of this writing, how this recovered 40,373 rsETH will be allocated remains at Kelpâs discretion, and no explicit confirmation has been provided. The current adapter balance of 40,373 rsETH is the only confirmed backing for all remote-chain rsETH across every L2 path, against total remote claims of 152,577 rsETH.

Ethereum mainne