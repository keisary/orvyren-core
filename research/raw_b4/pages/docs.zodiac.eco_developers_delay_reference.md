URL: https://docs.zodiac.eco/developers/delay/reference
TITLE: Contract reference: Delay Modifier
ERR: None

# Contract reference: Delay Modifier

Source: [zodiac-modifier-delay ](https://github.com/gnosisguild/zodiac-modifier-delay). The Delay Modifier is a Zodiac modifier: modules queue through it, and it forwards to the Safe.

## Setup

```
constructor(address _owner, address _avatar, address _target, uint256 _cooldown, uint256 _expiration)
function setUp(bytes memory initParams) public initializer
```

`initParams` decodes as `(address owner, address avatar, address target, uint256 cooldown, uint256 expiration)`. The expiration must be `0` or at least `60` seconds. Emits `DelaySetup`.

## Owner functions

Owner functions
| Function | Description |
|---|---|
| `setTxCooldown(uint256 seconds)` | Set the wait time between queueing and execution. |
| `setTxExpiration(uint256 seconds)` | Set the validity window after the cooldown. `0` means no expiration; otherwise at least `60`. |
| `setTxNonce(uint256 nonce)` | Skip queued transactions. The new nonce must be greater than `txNonce` and at most `queueNonce`. |
| `enableModule(address)` / `disableModule(address, address)` | Manage which callers can queue transactions. |

## Queue functions (enabled modules)

The queue functions return `success = true` when the transaction is queued. A calling module must not read this as “executed”.

## Execution functions (anyone)

Execution is strictly first-in, first-out. `executeNextTx` always addresses the transaction at `txNonce`.

## Views and state

Views and state
| Getter | Returns |
|---|---|
| `txCooldown()` / `txExpiration()` | The current configuration, in seconds. |
| `txNonce()` | The index of the next transaction to execute. |
| `queueNonce()` | The index for the next queued transaction. |
| `txHash(uint256)` / `getTxHash(uint256)` | The stored hash for a queue index. |
| `txCreatedAt(uint256)` / `getTxCreatedAt(uint256)` | The queue timestamp for an index. |
| `getTransactionHash(to, value, data, operation)` | Computes `keccak256(abi.encodePacked(to, value, data, operation))`. |
| `avatar()` / `target()` / `owner()` | The wiring of this instance. |

## Events

```
event DelaySetup(address indexed initiator, address indexed owner, address indexed avatar, address target);
event TransactionAdded(uint256 indexed queueNonce, bytes32 indexed txHash, address to, uint256 value, bytes data, Operation operation);
event TxCooldownSet(uint256 cooldown);
event TxExpirationSet(uint256 expiration);
event TxNonceSet(uint256 nonce);
```

## Mastercopies

Mastercopies
| Version | Address | State |
|---|---|---|
| **1.1.1** | `0x824175b945838d127c1ca83cbce11d8e44f6df01` | **Current. Deploy this one.** |
| 1.1.0 | `0x01F8cabB808D7dE0dF4202D4B60C8310d2f1339b` | Vulnerable. Do not use. See [Security](/developers/security). |
| 1.0.1 | `0xd54895B1121A2eE3f37b502F507631FA1331BED6` | Old. |
| 1.0.0 | `0xD62129BF40CD1694b3d9D9847367783a1A4d5cB4` | Old. |
Addresses are the same on all supported chains. Deploy through the Module Proxy Factory (`0x000000000000aDdB49795b0f9bA5BC298cDda236`).

The repository’s `main` branch contains Delay 2.0.0. It adds `execTransactionWithSignature`, an EIP-712 path that lets a relayer queue a transaction that an enabled module has signed. Version 2.0.0 is not yet in the canonical address registry. This documentation describes the 1.1.1 behavior, which 2.0.0 keeps unchanged.

## Audits

Audits
| Report | Scope |
|---|---|
| G0 Group, September 2021 | Delay Modifier ([PDF ](https://github.com/gnosisguild/zodiac-modifier-delay/blob/main/audits/ZodiacDelayModuleSep2021.pdf)) |
| Gnosis, June 2026 | The 1.1.1 patch |