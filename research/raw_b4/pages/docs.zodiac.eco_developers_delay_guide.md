URL: https://docs.zodiac.eco/developers/delay/guide
TITLE: Delay guide: set up and operate
ERR: None

# Delay guide: set up and operate

This page shows how to deploy a Delay Modifier, wire it to a Safe, and run it day to day.

Prerequisites:

- A Safe on a [supported chain](/developers/roles/deployments#supported-chains).
- A decision on two numbers: the cooldown and the expiration, both in seconds.
Pick the cooldown so that your owners can really react: long enough to notice a bad transaction and to collect signatures for the cancellation. One hour is too short for a weekend attack. Common values are 1 to 7 days.

The expiration must be `0` (no expiration) or at least `60` seconds. With `0`, a queued transaction never expires: if you never execute or cancel it, it blocks the queue forever. Set an expiration unless you have a process that always drains the queue.

## Step 1: deploy the proxy

Define a `delay` node in your constellation and push. The Zodiac SDK deploys the modifier, enables it on the Safe, and enables the callers that queue transactions — a Roles Modifier, another module, or a trusted address — all in one apply. The [Delay quickstart](/developers/quickstart-delay) shows it end to end.

The setup parameters are `(owner, avatar, target, cooldown, expiration)`. For a plain setup, the owner, the avatar, and the target are all the Safe. See the [contract reference](/developers/delay/reference#setup) for the full signature.

Everything that the Delay Modifier’s enabled modules queue will execute after the cooldown, unless the owner cancels it. Enable only callers that you intend to supervise. Watch the queue (step 3).

## Step 2: queue and execute

An enabled module queues a transaction:

```
delay.execTransactionFromModule(to, value, data, operation);
```

After the cooldown, anyone executes the head of the queue by repeating the same data:

```
delay.executeNextTx(to, value, data, operation);
```

`executeNextTx` verifies the data against the stored hash. Read the queued original from the `TransactionAdded` event of the queue transaction.

## Step 3: watch the queue

Index or poll two values:

- `queueNonce` — grows when a transaction enters the queue.
- `txNonce` — grows when a transaction executes or is skipped.
When `queueNonce > txNonce`, transactions are waiting. Subscribe to `TransactionAdded` and alert the owners. The event carries the full transaction data, so the owners can review what is queued.

## Operate the queue

Operate the queue
| Situation | Action | Who |
|---|---|---|
| A queued transaction is bad. | Call `setTxNonce(n)` with `n` past the bad transaction. All skipped transactions are canceled. | Owner |
| Expired transactions block the head. | Call `skipExpired()`. It advances past all expired entries. | Anyone |
| The cooldown or expiration must change. | Call `setTxCooldown(seconds)` / `setTxExpiration(seconds)`. Applies to future checks, not per queued item. | Owner |
| A queued transaction must run. | Call `executeNextTx(to, value, data, operation)` with the exact queued data. | Anyone |
`setTxNonce` only moves forward, and at most to `queueNonce`. Cancellation is a Safe transaction: the owners must sign it within the cooldown window.

## Verify the setup

1. Queue a harmless test transaction through the enabled module.
2. Confirm that `executeNextTx` reverts with “Transaction is still in cooldown”.
3. Wait for the cooldown, execute, and confirm the effect on the Safe.
4. Queue a second test transaction, cancel it with `setTxNonce`, and confirm that it cannot execute.