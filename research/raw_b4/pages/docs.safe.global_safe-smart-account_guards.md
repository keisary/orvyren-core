URL: https://docs.safe.global/safe-smart-account/guards
TITLE: Safe Guards – Safe Docs
ERR: None

ℹ️

Safe Guards are used when there are restrictions on top of the `n`-out-of-`m` scheme.

Safe Guards can make checks before and after a Safe transaction. The check before a transaction can programmatically check all the parameters of the respective transaction before execution. The check after a transaction is called at the end of the transaction execution and can be used to perform checks on the final state of the Safe.

To read about different examples of Safe Guards, see the implementations from [Zodiac (opens in a new tab)](https://github.com/gnosisguild/zodiac-guard-scope) and [Yearn (opens in a new tab)](https://mirror.xyz/yearn-finance-engineering.eth/9uInM_sCrogPBs5qkFSNF6qe-32-0XLN5bty5wKLVqU).

![Image 1: diagram Safe Guards](https://docs.safe.global/_next/static/media/diagram-safe-guards.f256b37f.png)

‼️

**Important:** Since a Safe Guard has full power to block Safe transaction execution, a broken Guard can cause a denial of service for a Safe. Make sure to audit the Guard code and pay attention to recovery mechanisms.

Last updated on August 27, 2026

Was this page helpful?