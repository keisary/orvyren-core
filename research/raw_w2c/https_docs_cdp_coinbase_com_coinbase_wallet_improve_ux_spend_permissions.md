# URL: https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions
# fetched: 2026-10-15T03:02:10.118814Z

> ## Documentation Index
>
> Fetch the complete documentation index at: [/llms.txt](https://docs.cdp.coinbase.com/llms.txt)
>
> Use this file to discover all available pages before exploring further.

[Skip to main content](https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions#content-area)

## [​](https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions\#overview)  Overview

Spend Permissions let you designate a trusted `spender` that can move assets out of a user’s Coinbase Wallet on their behalf.After the user signs the permission, the `spender` can initiate transfers within the limits you define — no additional prompts, pop-ups, or signatures needed from the user. This powers seamless experiences such as subscription renewals, algorithmic trading, and automated payouts.Read more about the Spend Permission Manager contract and supported chains on [GitHub](https://github.com/coinbase/spend-permissions).

Spend Permissions in Coinbase Wallet (formerly known as Base App) are coming soon and will be supported in a future update.

If you’re using Sub Accounts, learn how Coinbase Wallet can automatically fund Sub Accounts and optionally skip approval prompts using [Auto Spend Permissions](https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/sub-accounts#auto-spend-permissions).

## [​](https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions\#usage)  Usage

### [​](https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions\#request-a-spend-permission)  Request a Spend Permission

You create an EIP-712 payload that describes the permission and ask the user to sign it. Store the resulting signature along with the permission data so you can register the permission on-chain later. The SDK helper below handles construction and signing for you.

| Field Name | Type | Description |
| --- | --- | --- |
| `account` | `address` | Smart account this spend permission is valid for |
| `spender` | `address` | Entity that can spend `account`’s tokens |
| `token` | `address` | Token address (ERC-7528 native token or ERC-20 contract) |
| `allowance` | `uint160` | Maximum allowed value to spend within each `period` |
| `period` | `uint48` | Time duration for resetting used `allowance` on a recurring basis (seconds) |
| `start` | `uint48` | Timestamp this spend permission is valid starting at (inclusive, unix seconds) |
| `end` | `uint48` | Timestamp this spend permission is valid until (exclusive, unix seconds) |
| `salt` | `uint256` | Arbitrary data to differentiate unique spend permissions with otherwise identical fields |
| `extraData` | `bytes` | Arbitrary data to attach to a spend permission which may be consumed by the `spender` |

Request a Spend Permission

```
import { requestSpendPermission } from "@base-org/account/spend-permission";
import { createBaseAccountSDK } from "@base-org/account";
import { base } from "viem/chains";

const sdk = createBaseAccountSDK({
  appName: 'Coinbase Wallet SDK Demo',
  appLogoUrl: 'https://base.org/logo.png',
  appChainIds: [base.id],
});

const permission = await requestSpendPermission({
  account: "0x...",
  spender: "0x...",
  token: "0x...",
  chainId: 8453, // or any other supported chain
  allowance: 1_000_000n,
  periodInDays: 30,
  provider: sdk.getProvider(),
});

console.log("Spend Permission:", permission);
```

See all 21 lines

### [​](https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions\#use-the-spend-permission)  Use the Spend Permission

Using a permission is 2 steps:

1. **Prepare the calls** — Call `prepareSpendCallData` with the permission and the requested `amount`.
2. **Submit the calls** — Submit the calls using your app’s spender account.

`prepareSpendCallData` returns an array of calls needed to spend the tokens:

- `approveWithSignature` — When the permission is not yet registered onchain, this call would be prepended to the `spend` call.
- `spend` — The call to spend the tokens from the user’s Coinbase Wallet.

Prepare Spend Call Data

```
import { prepareSpendCallData } from "@base-org/account/spend-permission";

// returns [approveWithSignatureCall, spendCall]
const spendCalls = await prepareSpendCallData({
  permission,
  amount, // optional; omit to spend the remaining allowance
});

// If your app spender account supports wallet_sendCalls, submit them in batch using wallet_sendCalls
// this is an example on how to do it using wallet_sendCalls in provider interface
await provider.request({
  method: "wallet_sendCalls",
  params: [\
    {\
      version: "2.0",\
      atomicRequired: true,\
      from: spender,\
      calls: spendCalls,\
    },\
  ],
});

// If your app spender account doesn't support wallet_sendCalls, submit them in order using eth_sendTransaction
// this is an example on how to do it using eth_sendTransaction in provider interface
await Promise.all(
  spendCalls.map((call) =>
    provider.request({
      method: "eth_sendTransaction",
      params: [\
        {\
          ...call,\
          from: spender,\
        },\
      ],
    })
  )
);
```

See all 37 lines

**About the `spendCalls` array**This array has 2 calls when submitting the permission onchain for _the first time_.
When the permission is already registered onchain, this array has only 1 call (the `spend` call).For most use cases, you don’t need to worry about this.

### [​](https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions\#revoke-a-spend-permission)  Revoke a Spend Permission

You can revoke a permission in two ways:

- Request user approval via request to user’s Coinbase Wallet using `requestRevoke`.
- Revoke silently from your app’s spender by submitting the call returned from `prepareRevokeCallData`.

Revoke a Spend Permission

```
import {
  requestRevoke,
  prepareRevokeCallData,
} from "@base-org/account/spend-permission";

// Option A: User-initiated revoke (wallet popup)
try {
  const hash = await requestRevoke(permission);
  console.log("Revoke succeeded", hash);
} catch {
  console.warn("Revoke was rejected or failed");
}

// Option B: Silent revoke by your app's spender account
const revokeCall = await prepareRevokeCallData(permission);

// Submit the revoke call using your app's spender account
// this is an example on how to do it using wallet_sendCalls in provider interface
await provider.request({
  method: "wallet_sendCalls",
  params: [\
    {\
      version: "2.0",\
      atomicRequired: true,\
      from: spender,\
      calls: [revokeCall],\
    },\
  ],
});

// If your app spender account doesn't support wallet_sendCalls, submit the revoke call using eth_sendTransaction
// this is an example on how to do it using eth_sendTransaction in provider interface
await provider.request({
  method: "eth_sendTransaction",
  params: [\
    {\
      ...revokeCall,\
      from: spender,\
    },\
  ],
});
```

See all 41 lines

## [​](https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions\#api-reference)  API Reference

- [requestSpendPermission](https://docs.cdp.coinbase.com/coinbase-wallet/reference/spend-permission-utilities/requestSpendPermission)
- [prepareSpendCallData](https://docs.cdp.coinbase.com/coinbase-wallet/reference/spend-permission-utilities/prepareSpendCallData)
- [requestRevoke](https://docs.cdp.coinbase.com/coinbase-wallet/reference/spend-permission-utilities/requestRevoke)
- [prepareRevokeCallData](https://docs.cdp.coinbase.com/coinbase-wallet/reference/spend-permission-utilities/prepareRevokeCallData)
- [fetchPermissions](https://docs.cdp.coinbase.com/coinbase-wallet/reference/spend-permission-utilities/fetchPermissions)
- [fetchPermission](https://docs.cdp.coinbase.com/coinbase-wallet/reference/spend-permission-utilities/fetchPermission)
- [getPermissionStatus](https://docs.cdp.coinbase.com/coinbase-wallet/reference/spend-permission-utilities/getPermissionStatus)

## [​](https://docs.cdp.coinbase.com/coinbase-wallet/improve-ux/spend-permissions\#complete-integration-example)  Complete Integration Example

Complete Integration Example

```
import {
  fetchPermissions,
  fetchPermission,
  getPermissionStatus,
  prepareSpendCallData,
  requestSpendPermission,
  requestRevoke,
  prepareRevokeCallData,
} from "@base-org/account/spend-permission";

import { createBaseAccountSDK } from "@base-org/account";
import { base } from "viem/chains";

const sdk = createBaseAccountSDK({
  appName: 'Coinbase Wallet SDK Demo',
  appLogoUrl: 'https://base.org/logo.png',
  appChainIds: [base.id],
});

const spender = "0xAppSpenderAddress";

// 1) Fetch a specific permission by its hash
// Use fetchPermission when you already know the permission hash
// (e.g., stored from a previous session or passed as a parameter)
const permission = await fetchPermission({
  permissionHash: "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
  provider: sdk.getProvider(),
});

// Alternative: Fetch all permissions for a spender
// Use fetchPermissions when you need to see all available permissions
// and want to choose which one to use
// const permissions = await fetchPermissions({
//   account: "0xUserBaseAccountAddress",
//   chainId: 84532,
//   spender,
//   provider: sdk.getProvider(),
// });
// const permission = permissions.at(0);

// ========================================
// When there IS an existing permission
// ========================================

// 2. check the status of permission
try {
  const { isActive, remainingSpend } = await getPermissionStatus(permission);
  const amount = 1000n;

  if (!isActive || remainingSpend < amount) {
    throw new Error("No spend permission available");
  }
} catch {
  throw new Error("No spend permission available");
}

// 3. prepare the calls
const [approveCall, spendCall] = await prepareSpendCallData({
  permission,
  amount,
});

// 4. execute the calls using your app's spender account
// this is an example using wallet_sendCalls, in production it could be using eth_sendTransaction.
await provider.request({
  method: "wallet_sendCalls",
  params: [\
    {\
      version: "2.0",\
      atomicRequired: true,\
      from: spender,\
      calls: [approveCall, spendCall],\
    },\
  ],
});

// ========================================
// When there is NOT an existing permission
// ========================================

// 2. request a spend permission to use
const newPermission = await requestSpendPermission({
  account: "0xUserBaseAccountAddress",
  spender,
  token: "0xTokenContractAddress",
  chainId: 84532,
  allowance: 1_000_000n,
  periodInDays: 30,
  provider: sdk.getProvider(),
});

// 3. prepare the calls
const spendCalls = await prepareSpendCallData({
  permission: newPermission,
  amount: 1_000n,
});

// 4. execute the calls using your app's spender account
// this is an example using eth_sendTransaction. If your app account supports wallet_sendCalls, use wallet_sendCalls to batch the calls instead.
await Promise.all(
  spendCalls.map((call) =>
    provider.request({
      method: "eth_sendTransaction",
      params: [\
        {\
          ...call,\
          from: spender,\
        },\
      ],
    })
  )
);

// ========================================
// Request user to revoke spend permission
// ========================================

try {
  const hash = await requestRevoke(permission);
  console.log("Revoke succeeded", hash);
} catch {
  throw new Error("Revoke failed");
}

// ========================================
// Revoke spend permission in the background
// ========================================

const revokeCall = await prepareRevokeCallData(permission);

await provider.request({
  method: "wallet_sendCalls",
  params: [\
    {\
      version: "2.0",\
      atomicRequired: true,\
      from: spender,\
      calls: [revokeCall],\
    },\
  ],
});
```

See all 141 lines

Was this page helpful?

YesNo

Assistant

Responses are generated using AI and may contain mistakes.