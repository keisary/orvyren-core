URL: https://support.fireblocks.io/hc/en-us/articles/29210922951580-How-Policies-work
TITLE: How Policies work â Fireblocks Help Center
ERR: None

# How Policies work â Fireblocks Help Center
URL: https://support.fireblocks.io/hc/en-us/articles/29210922951580-How-Policies-work

How Policies work â Fireblocks Help Center

# How Policies work 

Understanding how the Policy Engine evaluates and applies rules is essential for creating effective Policies.

# Policy rules

Policy rules have two components that you can define:

- Parameters: Define which characteristics a transaction must "match" for the rule to apply. Scope: Who can initiate it? Where can it go to or from? Which asset is the rule for?
- Actions: Define what will happen next:

- Allow: The Policy Engine automatically approves and forwards to a designated signer.
- Approved by: Other users or user groups must approve or deny the allowed transaction. All of the associated user roles must be authorized approver user roles.
- Block: The Policy Engine automatically blocks the transaction.

# The first-match principle

Policies operate according to the first-match principle. For each submitted transaction, the Policy Engine scans the appropriate Policy from top to bottom and applies the first rule that it matches. The scan stops after a successful match. The top rule is checked first. If it is a match, it performs the rule's action. If not, rule two is checked, and so on.

Due to the first-match principle, the order of your rules is important for receiving the intended outcomes. For example, you may not want to place a rule that allows any transfer in any amount at the top of your Transfer Policy since most transactions would be allowed without needing to meet the stricter requirements in the other rules. Rules with overlapping parameters should be ordered so that higher priority rules are scanned first.

For security, the default block-all rule is always the last rule at the bottom of each Policy. If no other rule matches a transaction, the block-all rule blocks it.

# Example: Policy Engine applies the first-match principle to a transaction

John Smith, a trader at company XYZ, submits a transaction. In his company's workspace, he is assigned the following workspace role and user group:

- Role: Signer, authorized to sign transactions.
- User group: Traders, a custom group that John's company created in their workspace. The group has all traders with Signer roles.

John submits a transfer request for $500,000 of Bitcoin from his vault account to one of his whitelisted counterparties. His company's Transfer Policy has four rules.

After John submits the transfer request, the Policy Engine:

1. Skips rule one, which only applies when a Management group user is Initiator.
2. Skips rule two, which only applies to transactions greater than $1 million.
3. Applies rule three because the transaction matches each of its parameters. Sends the request to the approver defined under Action â for this rule, it is the Head of Trading.
4. After the Head of Trading approves the transaction, a signing request is sent to the Designated Signer. Since rule three sets Initiator as Designated Signer, John can then sign the transaction himself.

# Ordering your rules

It's important to p