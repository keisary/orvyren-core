# URL: https://grego.ai/reports/safe-abi-padding-permission-checks
# fetched: 2026-10-15T02:57:36.849234Z

Grego AI \| Gnosis Guild Zodiac Roles Modifier: Crafted MultiSend Payload Permission Bypass [Skip to content](https://grego.ai/reports/safe-abi-padding-permission-checks#main)

## Failure path

The MultiSend unwrapper bounded inner entries against padded outer calldata instead of the actual inner payload. A crafted final entry could make the permission checker approve attacker-controlled trailing bytes while MultiSend executed zeroes in their place.

## Impact and conditions

Permission-boundary failure. Exploitation required an already assigned role and affected only the final 1 to 31 trailing bytes of the last transaction.

Today we are disclosing another critical bug in the widely used [@zodiaceco](https://x.com/@zodiaceco) Roles Modifier Module with MultiSend unwrapping for [@safe](https://x.com/safe) wallets.

A reminder again that modules are used by Safe owners to expand the functionality of a Safe, but these also have full access to execute transactions, send funds, etc. so great care must be given to ensure these modules are bug free.

This finding was in the repo:

[https://github.com/gnosisguild/zodiac-modifier-roles](https://github.com/gnosisguild/zodiac-modifier-roles)

Team has acknowledged and fixed below and has been able to inform the majority of users to migrate to the updated version.

[https://github.com/gnosisguild/zodiac-modifier-roles/commit/1ddde84db9024c6c1898d1f4cf5dabded3e824f1](https://github.com/gnosisguild/zodiac-modifier-roles/commit/1ddde84db9024c6c1898d1f4cf5dabded3e824f1)

The Zodiac Roles app now shows a warning for mods that are still on the vulnerable version of the multisend unwrapper and offers a one-click migration to the fixed version.

If you would like to engage our AI security services for your protocol visit scan.grego.ai or contact [@0xriptide](https://x.com/@0xriptide) or [@0xitsgreg](https://x.com/@0xitsgreg)

Bug report follows …

## TLDR

A crafted MultiSend payload could circumvent permission checking and replace between 1 to 31 trailing bytes with zeroes. This is only possible for the last transaction and the last parameter in the multisend batch, so a function where a **trailing parameter** controls something critical. Attacker must already have a role assigned.

## Summary

The _MultiSendUnwrapper.\_validateEntries_ function uses _data.length_ (which includes ABI encoding padding of up to 31 bytes) instead of the actual inner bytes boundary when bounds-checking entry data. This allows a crafted multisend entry’s data field to extend into the ABI padding zone, creating a mismatch between the calldata the Roles Modifier’s permission checker verifies and the calldata MultiSend actually executes. A role member can exploit this to bypass function parameter restrictions — for instance, making the permission checker approve a transfer to an allowed treasury address while MultiSend executes the transfer to _address(0)_, permanently destroying the funds.

## Impact

The vulnerability breaks the Roles Modifier’s core security guarantee: that only permission-checked operations are executed through the Safe. For functions where critical parameters (particularly recipient addresses) appear near the end of the calldata, the permission checker can be made to verify completely different values than what MultiSend executes.

An example would be permanent fund destruction via functions where the recipient address is a trailing parameter. For a function like Aave’s _Pool.withdraw(address asset, uint256 amount, address to)_, the _to_ address falls in the padding zone, causing the permission checker to see the approved recipient while MultiSend passes _address(0)_. The withdrawn funds are sent to the zero address and permanently lost.

## Description

The Zodiac Roles Modifier enforces fine-grained permission restrictions on what transactions a module can execute through a Gnosis Safe. When a module submits a batched MultiSend transaction, the _MultiSendUnwrapper_ adapter parses the packed entries so each inner transaction can be individually permission-checked by _PermissionChecker.\_multiEntrypoint_. After all checks pass, the identical calldata is forwarded to the Safe, which delegate-calls MultiSend for execution.

The vulnerability arises because the unwrapper’s boundary check allows parsed entries to reference bytes _beyond_ the actual packed transaction content, into the ABI encoding padding zone, where the permission checker reads attacker-controlled values from calldata but MultiSend reads zeros from memory.

## The multiSend calldata layout

![MultiSend calldata layout: selector at byte 0, offset at byte 4, transaction length at byte 36, packed transaction bytes from byte 68 through 68 plus T, followed by up to 31 padding bytes.](https://grego.ai/assets/reports/safe-abi-padding-permission-checks/multisend-calldata-layout.png)

## The bug

_\_validateHeader_ correctly reads the inner bytes length T at line 43 and validates that _data.length == 4 + ceil32(64 + T)_. But T is a local variable and is **never passed** to _\_validateEntries_:

```
// MultiSendUnwrapper.sol — _validateHeader
uint256 length = uint256(bytes32(data[36:])); // T is read here
if (4 + _ceil32(32 + 32 + length) != data.length) {
    revert MalformedHeader();
}
```

_\_validateEntries_ uses _data.length_ as its boundary instead of _68 + T_:

```
// MultiSendUnwrapper.sol — _validateEntries (line 72)
uint256 length = uint256(bytes32(data[offset + 53:]));
if (offset + 85 + length > data.length) {  // BUG: uses data.length, not 68 + T
    revert MalformedBody();
}
```

The devs recognized the padding issue for the loop termination (line 58: _“data is padded to 32 bytes we can’t simply do offset < data.length”_) but did not apply the same reasoning to the entry data bounds check.

## The mismatch

When (64 + T) % 32 != 0, up to 31 bytes of ABI padding exist between the inner bytes boundary (68 + T) and data.length. An entry can declare a _dataLength_ that extends into this padding zone. The result:

![Comparison table: the permission checker reads calldata including attacker-controlled padding, while MultiSend copies only T bytes into memory and sees zeros.](https://grego.ai/assets/reports/safe-abi-padding-permission-checks/permission-checker-execution-mismatch.png)

The same data is used for both \_authorize and exec in Roles.sol (lines 109–117), with no intermediate re-validation.

## Recommended Fix

Pass the inner bytes boundary _68 + T_ from _\_validateHeader_ to _\_validateEntries_ and use it in the bounds check:

```
function unwrap(...) external pure returns (UnwrappedTransaction[] memory) {
    // ...
    uint256 innerEnd = _validateHeader(data);
    uint256 count = _validateEntries(data, innerEnd);
    return _unwrapEntries(data, count);
}

function _validateHeader(bytes calldata data) private pure returns (uint256 innerEnd) {
    // ... existing checks ...
    uint256 length = uint256(bytes32(data[36:]));
    if (4 + _ceil32(32 + 32 + length) != data.length) {
        revert MalformedHeader();
    }
    innerEnd = 68 + length;
}

function _validateEntries(bytes calldata data, uint256 innerEnd) private pure returns (uint256 count) {
    uint256 offset = OFFSET_START;
    for (; offset + 32 < innerEnd; ) {   // use innerEnd, not data.length
        // ...
        uint256 length = uint256(bytes32(data[offset + 53:]));
        if (offset + 85 + length > innerEnd) {  // use innerEnd, not data.length
            revert MalformedBody();
        }
        offset += 85 + length;
        count++;
    }
    if (count == 0) {
        revert MalformedBody();
    }
}
```

## Related public reports

- Safe · Zodiac Reality Module



  ### [Gnosis Safe Drain via Spoofed Question Rendering](https://grego.ai/reports/safe-rendered-question-hidden-transactions)

- Safe · Safe4337Module



  ### [Permanent ERC-4337 DoS for Safe v1.5.0 passkey accounts via Safe4337Module](https://grego.ai/reports/safe-passkey-validation)

- Yearn · yYB



  ### [Yearn yYB: Unbacked double mint and liquidity drain](https://grego.ai/reports/yearn-stale-operator-double-minting)