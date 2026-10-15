URL: https://docs.tenderly.co/monitoring/alerts/api.md
TITLE: Using Alerts API
ERR: None

> Documentation IndexFetch the complete documentation index at: https://docs.tenderly.co/llms.txt
> Use this file to discover all available pages before exploring further.

# Using Alerts API
> Configure simple and compound alerting rules programmatically with the Tenderly Alerts API, covering each expression type and multi-condition combinations.
This guide covers setting up both simple and complex alerting rules using Tenderly's API. We'll explore each expression type and then combine them into sophisticated monitoring solutions.
<Card title="Alerting API reference" href="/api-reference" />

## Introduction
Tenderly's Alert API allows you to create simple and complex Alerts.
A simple alert consists of one rule, for example `method_call` will get triggered when a transaction invokes your public or external method. A complex alert can have several conditions, and will get triggered when all of them are met. For example, an alert with `method_call` and `state_change` will trigger when a transaction calls the given method and updates the specified storage slot.

...

## Expression Types
### Notes
* These are all the expression types the API accepts. A payload with any other `type` value is rejected with a `400` ("Expressions are not in the right format").
* All expressions within an alert are AND-ed: the alert fires only when every expression matches the same transaction. To monitor independent conditions, create a separate alert for each.
* For comparison operators (`operator`), valid values are: `>`, `>=`, `<`, `<=`, `==`, `!=`, `contains`, `notContains`

...

For more details, explore the [Alerting API reference](/api-reference).

...

## Simple expressions examples
### 1. Method Call Monitoring
`bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}     curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" \     --header "Content-Type: application/json" \     --header "X-Access-Key: ${TENDERLY_API_KEY}" \     --data-raw '{       "name": "Critical Function Call Alert",       "description": "Monitors calls to critical functions",       "enabled": true,       "expressions": [         {

...

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
method_call_alert = {
"name": "Critical Function Call Alert",
"description": "Monitors calls to critical functions",
"enabled": True,
"expressions": [{
"type": "method_call",
"expression": {
"address": "0xe592427a0aece92de3edee1f18e0157c05861564",
"signature": {
"function_name": "unwrapWETH9",
"input_types": ["uint256", "address"]
}
}
},
{
"type": "contract_address",
"expression": {
"address": "0xe592427a0aece92de3edee1f18e0157c05861564"
}
}],
"delivery_channels": [{
"id": "your_channel_id",
"enabled": True
}]
}
```
response = requests.post(
    f"{base_url}/account/{ACCOUNT_ID}/project/{PROJECT_SLUG}/alert",
    headers=headers,
    json=method_call_alert
)
```
```
</Tab>
</Tabs>

...

### 2. State Change Monitoring
`bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}     curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" \     --header "Content-Type: application/json" \     --header "X-Access-Key: ${TENDERLY_API_KEY}" \     --data-raw '{       "name": "Critical State Change Alert",       "description": "Monitors important state changes",       "enabled": true,       "expressions": [{         "type":

...

### 3. Event Monitoring
`bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}     curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" \     --header "Content-Type: application/json" \     --header "X-Access-Key: ${TENDERLY_API_KEY}" \     --data-raw '{       "name": "Large Transfer Event Alert",       "description": "Monitors large transfer events",       "enabled": true,       "expressions": [{         "type":

...

## Complex Alert Examples
### 1. Security Monitoring System
`bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}     curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" \     --header "Content-Type: application/json" \     --header "X-Access-Key: ${TENDERLY_API_KEY}" \     --data-raw '{       "name": "Security Monitoring System",       "description": "Comprehensive security monitoring for contract",       "enabled": true,       "expressions": [

...

### 2. DeFi Protocol Monitor
```javascript theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
const defiAlerts = [
// Alert 1: large swaps via events
{
name: "Large Swaps",
description: "Swap events moving 1000+ tokens out of the pool",
enabled: true,
expressions: [{
type: "emitted_log",
expression: {
address: "0xpool_address",
event_name: "Swap",
event_id: "0x...", // Swap event signature
parameter_conditions: [
{
parameter_name: "amountOut",
parameter_type: "uint",
operator: ">=",
comparison_value: "1000000000000000000000" // 1000 tokens
}
],
decode_events: true
}
}],
delivery_channels: [{ id: "your_channel_id", enabled: true }]
},
// Alert 2: liquidity changes
{
name: "Liquidity Shift",
description: "Pool reserves moved by 10% or more",
enabled: true,
expressions: [{
type: "state_change",
expression: {
address: "0xpool_address",
parameter_conditions: [
{
parameter_name: "reserve0",
parameter_type: "uint",
compare_percentage: true,
comparison_value: "10",

...

```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
# Alert 1: large swaps via events
curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" 
--header "Content-Type: application/json" 
--header "X-Access-Key: ${TENDERLY_API_KEY}" 
--data-raw '{
"name": "Large Swaps",
"description": "Swap events moving 1000+ tokens out of the pool",
"enabled": true,
"expressions": [{
"type": "emitted_log",
"expression": {
"address": "0xpool_address",
"event_name": "Swap",
"event_id": "0x...",
"parameter_conditions": [
{
"parameter_name": "amountOut",
"parameter_type": "uint",
"operator": ">=",
"comparison_value": "1000000000000000000000"
}
],
"decode_events": true
}
}],
"delivery_channels": [{ "id": "your_channel_id", "enabled": true }]
}'
```
# Alert 2: liquidity changes
curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" \
--header "Content-Type: application/json" \
--header "X-Access-Key: ${TENDERLY_API_KEY}" \
--data-raw '{
  "name": "Liquidity Shift",
  "description": "Pool reserves moved by 10% or more",
  "enabled": true,
  "expressions": [{
    "type": "state_change",
    "expression": {
      "address": "0xpool_address",
      "parameter_conditions": [
        {
          "parameter_name": "reserve0",
          "parameter_type": "uint",
          "compare_percentage": true,
          "comparison_value": "10",
          "operator": ">="
        },
        {
          "parameter_name": "reserve1",
          "parameter_type": "uint",
          "compare_percentage": true,
          "comparison_value": "10",
          "operator": ">="
        }
      ]
    }
  }],
  "delivery_channels": [{ "id": "your_channel_id", "enabled": true }]
}'

# Alert 3: failed transactions on the pool
curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" \
--header "Content-Type: application/json" \
--header "X-Access-Key: ${TENDERLY_API_KEY}" \
--data-raw '{
  "name": "Failed Transactions",
  "description": "Failed transactions involving the pool",
  "enabled": true,
  "expressions": [
    {
      "type": "contract_address",
      "expression": { "address": "0xpool_address" }
    },
    {
      "type": "tx_status",
      "expression": { "transaction_success": false }
    }
  ],
  "delivery_channels": [{ "id": "your_channel_id", "enabled": true }]
}'
```
```

...

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
defi_alerts = [
# Alert 1: large swaps via events
{
"name": "Large Swaps",
"description": "Swap events moving 1000+ tokens out of the pool",
"enabled": True,
"expressions": [{
"type": "emitted_log",
"expression": {
"address": "0xpool_address",
"event_name": "Swap",
"event_id": "0x...",
"parameter_conditions": [
{
"parameter_name": "amountOut",
"parameter_type": "uint",
"operator": ">=",
"comparison_value": "1000000000000000000000"
}
],
"decode_events": True
}
}],
"delivery_channels": [{"id": "your_channel_id", "enabled": True}]
},
# Alert 2: liquidity changes
{
"name": "Liquidity Shift",
"description": "Pool reserves moved by 10% or more",
"enabled": True,
"expressions": [{
"type": "state_change",
"expression": {
"address": "0xpool_address",
"parameter_conditions": [
{
"parameter_name": "reserve0",
"parameter_type": "uint",
"compare_percentage": True,

...

```
for alert in defi_alerts:
    response = requests.post(
        f"{base_url}/account/{ACCOUNT_ID}/project/{PROJECT_SLUG}/alert",

[... middle omitted — see footer ...]

delivery_channels: [{ id: "your_channel_id", enabled: true }]
},
// Alert 3: total supply changes
{
name: "Supply Change",
description: "totalSupply moved by 1% or more",
enabled: true,
expressions: [{
type: "state_change",
expression: {
address: "0xtoken_address",
parameter_conditions: [
{
parameter_name: "totalSupply",
parameter_type: "uint",
compare_percentage: true,
comparison_value: "1",
operator: ">="
}
]
}
}],
delivery_channels: [{ id: "your_channel_id", enabled: true }]
}
];

...

```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
# Alert 1: Transfer event consistency
curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" 
--header "Content-Type: application/json" 
--header "X-Access-Key: ${TENDERLY_API_KEY}" 
--data-raw '{
"name": "Transfer Consistency",
"description": "Transfer events inconsistent with balance changes",
"enabled": true,
"expressions": [{
"type": "erc20_transfer_matcher",
"expression": {
"address": "0xtoken_address",
"log_name": "Transfer",
"balances": "balances"
}
}],
"delivery_channels": [{ "id": "your_channel_id", "enabled": true }]
}'
```
# Alert 2: large transfers
curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" \
--header "Content-Type: application/json" \
--header "X-Access-Key: ${TENDERLY_API_KEY}" \
--data-raw '{
  "name": "Large Transfers",
  "description": "Transfers of 1000+ tokens",
  "enabled": true,
  "expressions": [{
    "type": "emitted_log",
    "expression": {
      "address": "0xtoken_address",
      "event_name": "Transfer",
      "event_id": "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
      "parameter_conditions": [
        {
          "parameter_name": "value",
          "parameter_type": "uint",
          "operator": ">=",
          "comparison_value": "1000000000000000000000"
        }
      ]
    }
  }],
  "delivery_channels": [{ "id": "your_channel_id", "enabled": true }]
}'

# Alert 3: total supply changes
curl -X POST "https://api.tenderly.co/api/v1/account/${ACCOUNT_ID}/project/${PROJECT_SLUG}/alert" \
--header "Content-Type: application/json" \
--header "X-Access-Key: ${TENDERLY_API_KEY}" \
--data-raw '{
  "name": "Supply Change",
  "description": "totalSupply moved by 1% or more",
  "enabled": true,
  "expressions": [{
    "type": "state_change",
    "expression": {
      "address": "0xtoken_address",
      "parameter_conditions": [
        {
          "parameter_name": "totalSupply",
          "parameter_type": "uint",
          "compare_percentage": true,
          "comparison_value": "1",
          "operator": ">="
        }
      ]
    }
  }],
  "delivery_channels": [{ "id": "your_channel_id", "enabled": true }]
}'
```
```

...

```
for alert in token_alerts:
    response = requests.post(
        f"{base_url}/account/{ACCOUNT_ID}/project/{PROJECT_SLUG}/alert",
        headers=headers,
        json=alert
    )
```
```
</Tab>
</Tabs>

──────── [TRUNCATED] ────────
Showing 8,994 chars (head) + 2,990 chars (tail) of 12,091 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\docs.tenderly.co-2d1c877903.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\docs.tenderly.co-2d1c877903.md" offset=267 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────