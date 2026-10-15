# URL: https://docs.roles.gnosisguild.org/general/conditions
# fetched: 2026-10-15T02:56:09.971493Z

[Skip to Content](https://docs.roles.gnosisguild.org/general/conditions#nextra-skip-nav)

General ConceptsConditions

# Conditions

Zodiac Roles implements a robust conditions system that allows for defining complex conditions over calldata and ether value.

A condition is represented by a tree structure.
Each node in the tree defines a condition [operator](https://docs.roles.gnosisguild.org/general/conditions#operator) and specifies a [parameter type](https://docs.roles.gnosisguild.org/general/conditions#paramType) for the value in scope.
Evaluating the condition tree on transaction calldata starts at the root node.
As the tree is traversed the calldata is decoded and specific ranges are plucked according to the parameter type definitions specified with the nodes.

## Node Properties [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#node-properties)

Each condition node is defined by the following properties:

### `paramType` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#paramtype)

Specifies how to decode and pluck the parameter value from calldata. It can be one of the following:

| Value | Description |
| --- | --- |
| **`Static`** | Interpret the word currently in scope as a static value, i.e., a value with a fixed length padded to 32 bytes. |
| **`Dynamic`** | Interpret the word currently in scope as an offset to a dynamic length value, i.e., `bytes` or `string`. |
| **`Tuple`** | Decode the value as a tuple. The `children` condition nodes inform the types of the tuple’s fields. |
| **`Array`** | Interpret the word as an offset to a dynamic length array. The `children` condition nodes inform the array element type. |
| **`AbiEncoded`** | Decode the value using standard ABI decoding. The `children` condition nodes inform the individual field types. |
| **`Calldata`** | Decode the value like `AbiEncoded`, but skip the first 4 bytes (function selector). |
| **`None`** | Used with logical expressions. The `children` condition nodes inform how to interpret the current scope. |

### `children` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#children)

An array of sub conditions, used for any of the following purposes:

- Inform the decoding of complex types by defining types of their fields or elements (required for `ParamType.AbiEncoded`, `ParamType.Calldata`, `ParamType.Tuple`, `ParamType.Array`)
- Set conditions on specific fields of a tuple type value (via `Operator.Matches`)
- Set conditions on elements of an array type value (via `Operator.ArrayEvery`)
- Define branch conditions for n-ary logical operators (`Operator.And`, `Operator.Or`)

### `operator` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#operator)

Defines the conditional operation to apply to the value plucked from calldata. (Refer to the [Operators](https://docs.roles.gnosisguild.org/general/conditions#operators) section for a list of available operators.)

### `compValue` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#compvalue)

Defines the value to compare against (only used with comparison operators).

## Operators [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#operators)

### `Matches` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#matches)

Allows setting conditions on selected fields of tuple type parameters.
Used with `ParamType.Calldata` it allows setting conditions on specific parameters of the function call.
Used with `ParamType.AbiEncoded` it allows setting conditions on selected ABI encoded variables within a bytes value.

### Comparisons [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#comparisons)

#### `EqualTo` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#equalto)

Checks equality of the plucked value to a given comparison value.

#### `EqualToAvatar` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#equaltoavatar)

Equivalent to using `EqualTo` with the avatar address as `compValue`.

This extra operator is provided for convenience and optimization, since comparing with the avatar address is a common operation. The avatar address is available to the condition evaluation function and therefore does not need to be stored as a comparison value.

#### `GreaterThan` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#greaterthan)

Checks that the plucked `uint` value is greater than the comparison value.

#### `LessThan` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#lessthan)

Checks that the plucked `uint` value is greater than the comparison value.

#### `SignedIntGreaterThan` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#signedintgreaterthan)

Checks that the plucked `int` value is greater than the comparison value.

#### `SignedIntLessThan` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#signedintlessthan)

Checks that the plucked `int` value is less than the comparison value.

#### `Bitmask` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#bitmask)

Checks that `bytes` value in scope matches the bitmask encoded in the comparison value.

The bitmask is packed into a `bytes32``compValue` in the following way:

```

<bytes2 offset><bytes15 mask><bytes15 expected value>
```

- `offset` specifies the offset in bytes from the start of the `bytes` value to the first byte that should be masked.
- `mask` specifies which bytes should be checked. A `1` bit means that the bit at the same position should be checked, a `0` bit means that the bit should be ignored.
- `expected value` specifies the expected values of the bits under the mask.

### Array Expressions [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#array-expressions)

#### `ArrayEvery` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#arrayevery)

Checks that every element of the array matches the condition.

### Logical Expressions [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#logical-expressions)

Logical expressions are n-ary operators that take an array of child conditions and combine their evaluation results.
Generally having a `paramType` of `None` logical expressions do not change the evaluation scope, meaning that every child condition will address the same calldata range.

#### `And` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#and)

Checks that every child condition evaluates to `true`.

#### `Or` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#or)

Checks that at least one of the child conditions evaluates to `true`.

### Allowance Expressions [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#allowance-expressions)

[Allowances](https://docs.roles.gnosisguild.org/allowances) serve as a mechanism for tracking quotas.
Each allowance expression references a specific allowance in the `compValue` field by its `bytes32` key.
After a call passes the condition and has been successfully executed, all allowances consumed within the condition will be updated.
If the condition evaluates to `false` or executing the call reverts, allowances will not be updated.

#### `WithinAllowance` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#withinallowance)

Checks that the `uint` value in scope does not exceed the given allowance and consumes that amount.

#### `EtherWithinAllowance` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#etherwithinallowance)

Checks that the transaction’s ether value does not exceed the given allowance and consumes that amount.

#### `CallWithinAllowance` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#callwithinallowance)

Useful for tracking function call quotas, checks that the given allowance is not depleted and decrements it by \`1.

### `Pass` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#pass)

Allows any value. Used for condition nodes that are required solely for informing how to decode complex type value.

For example, defining the types of all fields of a tuple is necessary for correct decoding.

### `Custom` [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#custom)

Checks the value in scope against a [custom condition](https://docs.roles.gnosisguild.org/general/conditions#custom-conditions) defined in the `compValue` fields.

## Examples [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#examples)

### Balancer swap [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#balancer-swap)

The following condition enforces that the Balancer [single swap](https://docs.balancer.fi/integration-guides/swapping/swapping-custom-paths-with-router.html#single-swap) function must only be used to swap WETH for DAI and vice versa. Additionally, the sender and recipient for the swap must be set to the avatar address.

ABI inputs

- singleSwap

`tuple`





  - poolId

    `bytes32`

  - kind

    `uint8`

  - assetIn

    `address`

  - assetOut

    `address`

  - amount

    `uint256`

  - userData

    `bytes`
- funds

`tuple`





  - sender

    `address`

  - fromInternalBalance

    `bool`

  - recipient

    `address`

  - toInternalBalance

    `bool`
- limit

`uint256`

- deadline

`uint256`


condition

- Matches

`Calldata`





  - Matches

    `Tuple`





    - EqualTo

      `0x0b09dea1…0000001a``Static`

    - Pass

      `Static`

    - Or

      `None`





      - EqualTo

        `0xc02aaa39…3c756cc2``Static`

      - EqualTo

        `0x6b175474…95271d0f``Static`
    - Or

      `None`





      - EqualTo

        `0xc02aaa39…3c756cc2``Static`

      - EqualTo

        `0x6b175474…95271d0f``Static`
    - Pass

      `Static`

    - Pass

      `Dynamic`
  - Matches

    `Tuple`





    - EqualToAvatar

      `Static`

    - Pass

      `Static`

    - EqualToAvatar

      `Static`

    - Pass

      `Static`

✅ example call data (valid)

⛔ example call data (violation)

```
0x
```

```
52bbbe2900000000000000000000000000000000000000000000000000000000000000e00000000000000000000000004f2083f5fbede34c2714affb3105539775f7fe6400000000000000000000000000000000000000000000000000000000000000000000000000000000000000004f2083f5fbede34c2714affb3105539775f7fe640000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000010b09dea16768f0799065c475be02919503cb2a3500020000000000000000001a0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000006b175474e89094c44da98b954eedeac495271d0f000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000c000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
```

```
      sender: avatar address    recipient: avatar address        WETH/DAI pool ID    WETH token address  DAI token address
```

The root condition node generally targets the entire calldata range after the 4 bytes function selector. It uses a `ParamType.Calldata` matches structure defining how to decode the bytes in that range.

We define `Operator.Matches` checks on both tuples.

- For `singleSwap` an exact match on the `poolId` fields is required.
- For the `assetIn` and `assetOut` fields, the values must be either `WETH` or `DAI` using `Operator.Or`.
- For `swapInfo` the `sender` and `recipient` fields must be set to the address of the avatar using `Operator.EqualToAvatar`.

This example shows `Operator.Matches` being used to set conditions on specific fields of a tuple type value.

## Custom conditions [Permalink for this section](https://docs.roles.gnosisguild.org/general/conditions\#custom-conditions)

Custom conditions can be defined by implementing the `ICustomCondition` interface. For an example of a custom condition, refer to the `AvatarIsOwnerOfERC721.sol` contract.

Importantly, custom conditions must not maintain a state that is updated for every transaction passing through the check. This is because, at the level of the custom condition, there is no way to determine whether or not the transaction will ultimately be executed.

Last updated onAugust 25, 2026

[Introduction](https://docs.roles.gnosisguild.org/ "Introduction") [Allowances](https://docs.roles.gnosisguild.org/general/allowances "Allowances")

* * *