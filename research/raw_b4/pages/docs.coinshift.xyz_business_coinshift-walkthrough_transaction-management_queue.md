URL: https://docs.coinshift.xyz/business/coinshift-walkthrough/transaction-management/queue
TITLE: Queue | Business | Coinshift
ERR: None

# Queue | Business | Coinshift
URL: https://docs.coinshift.xyz/business/coinshift-walkthrough/transaction-management/queue

# Queue

In Coinshift's multi-sig Safes, queued transactions require manual execution. To maintain the state and balance of your Safe effectively, transactions must be executed in the order they are queued. If a transaction is executed out of order, it will be frozen until resolved.

To avoid this issue, examine the Nonce field and execute transactions with smaller nonce values before progressing to those with higher nonce values.

For additional clarification, we highly recommend watching the below GIF closely. It explains why it's important to execute the transactions in the right order.

Observe the cautionary message displayed when a user attempts to execute the most recent transaction without first processing the existing queued transactions. 

Upon receiving the necessary number of signatures, which meets Safe's threshold, a transaction is ready for execution.

Click on the transaction.

Locate and select the Execute option to submit the transaction to the network.

Successfully executed transactions will appear in the History tab.

Signers who fulfill Safe's threshold with their transaction approval may utilise a streamlined command called Approve and Execute. This command allows the Signer to approve and execute the transaction in one step, rather than performing two separate actions.

---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://docs.coinshift.xyz/business/coinshift-walkthrough/transaction-management/queue.md?ask=<question>

```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.