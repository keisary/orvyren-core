URL: https://docs.safe.global/advanced/smart-account-guards
TITLE: Safe Guards – Safe Docs
ERR: None

[](https://docs.safe.global/) [Home Home](https://docs.safe.global/home/what-is-safe) [SDK SDK](https://docs.safe.global/sdk/overview) [API API](https://docs.safe.global/core-api/api-overview) [Contracts Contracts](https://docs.safe.global/advanced/smart-account-overview) [Resource Hub Resource Hub](https://docs.safe.global/resource-hub) [GitHub (opens in a new tab)](https://github.com/safe-global)
[Question? Give us feedback → (opens in a new tab)](https://github.com/safe-global/safe-docs/issues/new?assignees=&labels=nextra-feedback&projects=&template=nextra-feedback.yml&title=%5BFeedback%5D+) [Edit this page](https://github.com/safe-global/safe-docs/tree/main/pages/advanced/smart-account-guards.mdx) Scroll to top

...

# Safe Guards
ℹ️
Safe Guards are introduced with [Safe contracts version 1.3.0 (opens in a new tab)](https://github.com/safe-global/safe-smart-account/blob/v1.3.0/CHANGELOG.md) .
Safe Guards are used when there are restrictions on top of the `n` -out-of- `m` scheme.

...

diagram Safe Guards
‼️
**Important:** Since a Safe Guard has full power to block Safe transaction
execution, a broken Guard can cause a denial of service for a Safe. Make sure
to audit the Guard code and pay attention to recovery mechanisms.

...

Was this page helpful?
[Report issue](https://github.com/safe-global/safe-docs/issues/new?assignees=&labels=nextra-feedback&projects=&template=nextra-feedback.yml&title=%5BFeedback%5D+)
[](https://safe.global/)
Developers