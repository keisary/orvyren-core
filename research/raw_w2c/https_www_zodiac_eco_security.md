# URL: https://www.zodiac.eco/security
# fetched: 2026-10-15T02:57:36.849234Z

Security

# The hard part of security is operational

Cryptography and audited contracts are table stakes. The losses that actually happen come from operations: a compromised dashboard, an overbroad keeper, a signer tricked into approving the wrong call. Zodiac makes the operational layer enforceable: every policy a rule the chain checks before funds can move, not a procedure a human is trusted to follow.

Why operational

## Most losses aren’t a bug in the code.  They’re a gap in operations.

Keys get split and contracts get audited, yet funds still leave. The controls that govern day-to-day operations live in a document people are trusted to follow, and an attacker only has to compromise one interface or fool one signer.

Trusted to be followed

### Policy as a document

- Procedures in a runbook
- Spending limits in a spreadsheet
- Approvals a person can be tricked into

Checked on every transaction

### Policy the chain enforces

- Approval workflows are enforced, not just assumed
- Limits hold even when a signer is tricked
- Every rule runs against the chain’s live, current state

Zodiac turns operational policy into bytecode the chain enforces. Nothing to skip, bypass, or socially engineer.

If your security now rests on the chain enforcing that policy, the obvious question is whether the enforcement itself holds. The rest of this page answers it.

Our claims

## Built to survive a compromise

01

### Open and onchain, not a vendor black box

A vendor policy engine is a closed system you have to trust to secure its own infrastructure, stay up under load, and keep enforcing in the volatile market conditions where you most need to transact. That is a single point of failure you do not control. Zodiac’s policy engine is open and runs onchain, so as long as the chain you are transacting on is live, your enforcement is live with it. No closed infrastructure to depend on, and no vendor lock-in.

02

### Defense in depth, by construction

The layers fail independently. A stolen signer key is stopped by the multisig threshold, and a tricked signer or a compromised interface is stopped by the onchain policy above it. Signing stays standard, so each signer can sit behind a hardware wallet or HSM. No other policy engine composes with your existing key custody this way.

03

### Enforced at the last line of defense

Every layer above the chain can be subverted. A host can lie, a dashboard can be swapped, a hardware attestation can be forged. The chain cannot. The policy is part of the transaction itself: the account checks every call against its rules as it executes, and anything that breaks a rule simply reverts. Whatever was compromised upstream, the chain still decides the outcome.

The Safe foundation

## Standing on the most-deployed smart account stack

Zodiac extends Safe, inheriting the security perimeter that Safe has built over seven years of production deployment, audited by the firms institutional buyers already know.

- ### $100B+ secured


Safe accounts hold the majority of institutional onchain value. The custody perimeter is the same one your peers already trust.

- ### 18+ audits


Safe is audited by Ackee, Runtime Verification, OpenZeppelin, Certora, and others. Reports are public.

- ### Trusted by Safe


Zodiac modules are used in production by the Safe team and recognized across the wider Safe ecosystem.


See [safe.global/security](https://safe.global/security) for the Safe team’s security posture. Everything there applies to your Zodiac deployment by construction.

Audits

## Zodiac modules in production, audited

Independent firms have reviewed the Zodiac modules that enforce policy on top of the stack.

- [![Omniscia](https://www.zodiac.eco/logos/omniscia.svg)\\
Omniscia](https://omniscia.io/)
- [![G0 Group](https://www.zodiac.eco/logos/g0-group.png)\\
G0 Group](https://github.com/g0-group/Audits)
- [![Gnosis](https://www.zodiac.eco/logos/gnosis.svg)\\
Gnosis](https://www.gnosis.io/)

For the full list of module reports, contact [security@zodiac.eco](mailto:security@zodiac.eco).

Threat model

## What we protect and what we don’t

- ### Trust assumptions


You trust the chain to execute correctly. You trust audited Safe contracts. You trust the audited Zodiac modules you’ve deployed. Our interface sits in the path you normally use, but it is not a required dependency: if it goes down you can sign through another interface or execute against the contracts directly, and the onchain policy enforces the same rules either way.

- ### What an attacker controlling a signer key can do


Only what that signer’s role permits. They cannot drain funds outside the role, grant themselves new permissions, or modify the policy structure without separate authorization.

- ### What an attacker controlling our infrastructure can do


Nothing to your funds. Our app, our SDK, and our extension help you build policies, but the deployed contracts execute on the chain without our involvement.

- ### What we cannot prevent


Bugs in the underlying protocols you’re interacting with. Oracle manipulation. Bugs in custom logic you deploy. The chain re-org or consensus failure. We bound damage from compromised authority; we do not replace audits of the contracts you call.


Further reading

[Threat landscape·May 14, 2026·12 min read\\
**April 2026 was the worst month on record for DeFi exploits** \\
A taxonomy of the incidents — compromised admin keys, overbroad keepers, unsafe configs — and an honest accounting of which classes onchain policy bounds and which it doesn’t.\\
Read post →](https://www.zodiac.eco/blog/april-2026-defi-hacks)

## Want to walk through the threat model with us?

We’ll demo the full stack against your specific operating model and risk requirements.

[Get started](https://www.zodiac.eco/get-started) [Book a demo](https://calendar.proton.me/bookings#CIEqv8uHWc0TcEx71Ug7m3bAx5dFmBjW6XNi1l7LrnI=)

or see [how we compare to MPC](https://www.zodiac.eco/vs/mpc)