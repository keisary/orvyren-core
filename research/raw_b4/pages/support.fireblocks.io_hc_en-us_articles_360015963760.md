URL: https://support.fireblocks.io/hc/en-us/articles/360015963760
TITLE: Approval and signing notification expiration â Fireblocks Help Center
ERR: None

# Approval and signing notification expiration â Fireblocks Help Center
URL: https://support.fireblocks.io/hc/en-us/articles/360015963760
Author: Updated 
                 1 day ago

Approval and signing notification expiration â Fireblocks Help Center

Skip to main content

Fireblocks uses different security and safety mechanisms to prevent unauthorized workspace activity. One of these mechanisms is the expiration of approval and signing notifications.

Approvals are required for:

- New connections
- New users
- Transactions, per the workspace's Policies. For all outbound transactions, signing is required.

Except for email invitations, all notifications that require approval appear in the Fireblocks mobile app.

## Transaction authorization and signing notifications

### Transaction authorization expiration

Transactions fail if not authorized within the configured timeout window. The default is 2 hours from when the transaction is created. Approval is required before the initiator can sign when two-tier authorization is enabled in the Policy.

You can customize the timeout window up to a maximum of 24 hours or a minimum of 5 minutes, globally, per signing method, or per individual transaction. For configuration steps, see Transaction Timeout Configuration.

### Policy change request

Policy change requests using the Policy Editor expire after seven days if your workspace Owner and Admin Quorum have not yet approved them.

### Initiator signing expiration

Transactions are canceled if not signed within the configured timeout window. The default is 2 hours from when the transaction is created. Signing follows authorization if two-tier authorization is enabled in the Policy.

For timeout configuration options, see Transaction Timeout Configuration.

### Transaction timeout configuration

Workspace admins can configure how long Fireblocks waits for a transaction to be broadcast to the blockchain before marking it as failed. The default timeout is 2 hours. You can customize this up to a maximum of 24 hours or a minimum of 5 minutes, globally, per signing method, or per individual transactions, depending on your operational needs.

For configuration steps, limits, and a full explanation of how timeout layers interact, see Transaction Timeout Configuration.

## Whitelisting and connection approval notifications

Approval is required for new whitelisted addresses, exchange connections, Fireblocks P2P Network connections, and fiat account connections.

### Admin quorum expiration

Approvals requiring admin quorum expire after seven days.

## User approval notifications

### New user approval expiration (Owner)

Workspace Owners receive a notification when a new user is added to their workspace. The Owner must approve the new user request within seven days. Otherwise, the request expires and must be resubmitted. Approving this notification sends an email invitation to the new user.

### New user invitation expiration (User)

New users have seven days to respond to their Fireblocks email invitation and set up their new accounts. Contact Fireblocks Support if you need to extend this timeframe.

### Granting signing privileges expirat