# URL: https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview
# fetched: 2026-10-15T03:02:10.118814Z

For AI agents: a documentation index is available at [/llms.txt](https://docs.metamask.io/llms.txt). A markdown version of this page is available at the same URL with .md appended (or via Accept: text/markdown).

[Skip to main content](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#__docusaurus_skipToContent_fallback)

**Infura** docs have shifted to [docs.infura.io](https://docs.infura.io/).

On this page

Delegation is the ability for a [MetaMask smart account](https://docs.metamask.io/smart-accounts-kit/concepts/smart-accounts/) to grant permission to another smart contract
or externally owned account (EOA) to perform specific executions on its behalf.
The account that grants the permission is called the delegator account, while the account that receives the permission
is called the delegate account.

The Smart Accounts Kit follows the [ERC-7710](https://eips.ethereum.org/EIPS/eip-7710) standard for smart contract delegation.
In addition, users can use [delegation scopes](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/delegation-scopes/) and [caveat enforcers](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/caveat-enforcers/) to apply rules and restrictions to delegations.
For example, Alice delegates the ability to spend her USDC to Bob, limiting the amount to 100 USDC.

## Delegation types [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#delegation-types "Direct link to Delegation types")

You can create the following delegation types:

### Root delegation [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#root-delegation "Direct link to Root delegation")

A root delegation is when a delegator delegates their own authority away, as opposed to _redelegating_ permissions
they received from a previous delegation. In a chain of delegations, the first delegation is the root delegation.
For example, Alice delegates the ability to spend her USDC to Bob, limiting the amount to 100 USDC.

Use [`createDelegation`](https://docs.metamask.io/smart-accounts-kit/reference/delegation/#createdelegation) to create a root delegation.

### Open root delegation [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#open-root-delegation "Direct link to Open root delegation")

An open root delegation is a root delegation that doesn't specify a delegate. This means that any account can
redeem the delegation. For example, Alice delegates the ability to spend 100 of her USDC to anyone.

You must create open root delegations carefully, to ensure that they are not misused.
Use [`createOpenDelegation`](https://docs.metamask.io/smart-accounts-kit/reference/delegation/#createopendelegation) to create an open root delegation.

### Redelegation [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#redelegation "Direct link to Redelegation")

A delegate can redelegate permissions that have been granted to them, creating a chain of delegations across trusted parties.
For example, Alice delegates the ability to spend 100 of her USDC to Bob. Bob redelegates the ability to spend
50 of Alice's 100 USDC to Carol.

See [how to create a redelegation](https://docs.metamask.io/smart-accounts-kit/guides/delegation/create-redelegation/) guide to learn more.

### Open redelegation [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#open-redelegation "Direct link to Open redelegation")

An open redelegation is a redelegation that doesn't specify a delegate. This means that any account can redeem
the redelegation. For example, Alice delegates the ability to spend 100 of her USDC to Bob. Bob redelegates
the ability to spend 50 of Alice's 100 USDC to anyone.

As with open root delegations, you must create open redelegations carefully, to ensure that they are not misused.
Use [`createOpenDelegation`](https://docs.metamask.io/smart-accounts-kit/reference/delegation/#createopendelegation) to create an open redelegation.

## Attenuating authority [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#attenuating-authority "Direct link to Attenuating authority")

When creating chains of delegations via redelegations, it's important to understand how authority flows and can be restricted.

- Each delegation in the chain inherits all restrictions from its parent delegation.
- New caveats can add further restrictions, but can't remove existing ones.

This means that a delegate can only redelegate with equal or lesser authority than they received.

## Delegation flow [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#delegation-flow "Direct link to Delegation flow")

The delegation flow consists of the following steps:

Caveat enforcerDelegation ManagerDelegateDelegatorCaveat enforcerDelegation ManagerDelegateDelegatorHold delegation until redemptionExpect no errorExpect no errorExpect no errorExpect no errorExpect no errorCreate delegation with caveatenforcersSign delegationSend signed delegationredeemDelegations() with delegation &execution detailsisValidSignature()Confirm valid (or not)beforeAllHook()beforeHook()executeFromExecutor() with execution detailsPerform executionafterHook()afterAllHook()

### Step 1. Create a delegation [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#step-1-create-a-delegation "Direct link to Step 1. Create a delegation")

The delegator creates a delegation, configuring a [scope](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/delegation-scopes/) and
optional [caveats](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/caveat-enforcers/) that define the conditions under which the delegation can be redeemed.

### Step 2. Sign the delegation [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#step-2-sign-the-delegation "Direct link to Step 2. Sign the delegation")

The delegator signs the delegation, producing a verifiable signature that the [Delegation Manager](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/delegation-manager/) can later validate.

### Step 3. Send the signed delegation [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#step-3-send-the-signed-delegation "Direct link to Step 3. Send the signed delegation")

The delegator sends the signed delegation to the delegate. A dapp can store the delegation in the storage solution
of their choice (such as a local database, Filecoin, or other databases), enabling retrieval for future redemption.

### Step 4. Redeem the delegation [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#step-4-redeem-the-delegation "Direct link to Step 4. Redeem the delegation")

The delegate submits the signed delegation to the Delegation Manager by calling `redeemDelegations()` with the
delegation and execution details.

### Step 5. Validate the delegation [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#step-5-validate-the-delegation "Direct link to Step 5. Validate the delegation")

The Delegation Manager validates the input data by ensuring the lengths of `delegations`, `modes`, and
`executions` match. It also verifies delegation signatures, ensuring validity using ECDSA (for EOAs) or
`isValidSignature` (for contracts).

### Step 6. Execute `beforeHook` [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#step-6-execute-beforehook "Direct link to step-6-execute-beforehook")

If the signature validation passes, the Delegation Manager executes the `beforeHook` for each [caveat](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/caveat-enforcers/)
in the delegation, passing relevant data (`terms`, `arguments`, `mode`, `execution``calldata`, and `delegationHash`) to
the caveat enforcer.

### Step 7. Perform execution [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#step-7-perform-execution "Direct link to Step 7. Perform execution")

If `beforeHook` validation passes, the Delegation Manager calls `executeFromExecutor` to perform the delegation's
execution, either by the delegator or the caller for self-authorized executions.

### Step 8. Execute `afterHook` [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#step-8-execute-afterhook "Direct link to step-8-execute-afterhook")

The Delegation Manager runs each caveat enforcer's `afterHook` and `afterAllHook` to verify post-execution conditions.

See [how to perform executions on a smart account's behalf](https://docs.metamask.io/smart-accounts-kit/guides/delegation/execute-on-smart-accounts-behalf/) for a step-by-step guide.

## Delegation Framework [​](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview\#delegation-framework "Direct link to Delegation Framework")

The Smart Accounts Kit includes the Delegation Framework, a
[set of comprehensively audited smart contracts](https://github.com/MetaMask/delegation-framework) that
collectively handle smart account creation, the delegation lifecycle, and caveat enforcement.

It consists of the following components:

| Component | Description |
| --- | --- |
| [Delegation Manager](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/delegation-manager/) | Validates delegations and triggers executions on behalf of the delegator, ensuring tasks are executed accurately and securely. |
| [Caveat enforcers](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/caveat-enforcers/) | Manage rules and restrictions for delegations, providing fine-tuned control over delegated executions. |

On this page

- [Delegation types](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#delegation-types)
  - [Root delegation](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#root-delegation)
  - [Open root delegation](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#open-root-delegation)
  - [Redelegation](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#redelegation)
  - [Open redelegation](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#open-redelegation)
- [Attenuating authority](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#attenuating-authority)
- [Delegation flow](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#delegation-flow)
  - [Step 1. Create a delegation](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#step-1-create-a-delegation)
  - [Step 2. Sign the delegation](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#step-2-sign-the-delegation)
  - [Step 3. Send the signed delegation](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#step-3-send-the-signed-delegation)
  - [Step 4. Redeem the delegation](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#step-4-redeem-the-delegation)
  - [Step 5. Validate the delegation](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#step-5-validate-the-delegation)
  - [Step 6. Execute `beforeHook`](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#step-6-execute-beforehook)
  - [Step 7. Perform execution](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#step-7-perform-execution)
  - [Step 8. Execute `afterHook`](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#step-8-execute-afterhook)
- [Delegation Framework](https://docs.metamask.io/smart-accounts-kit/concepts/delegation/overview#delegation-framework)