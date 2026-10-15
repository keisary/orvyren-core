URL: https://docs.safe.global/core-api/transaction-service-guides/transactions
TITLE: Transactions with off-chain signatures – Safe Docs
ERR: None

# Transactions with off-chain signatures

This guide shows how to interact with the Safe Transaction Service API to create, sign, and execute transactions with the owners of a Safe account.

The different steps are implemented using [Curl (opens in a new tab)](https://github.com/curl/curl) requests, the [Safe{Core} SDK (opens in a new tab)](https://github.com/safe-global/safe-core-sdk) TypeScript library and the [safe-eth-py (opens in a new tab)](https://github.com/safe-global/safe-eth-py) Python library.

## Prerequisites

1. [Node.js and npm (opens in a new tab)](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm#using-a-node-version-manager-to-install-nodejs-and-npm) when using the Safe{Core} SDK.
2. [Python (opens in a new tab)](https://www.python.org/downloads/) >= 3.9 when using `safe-eth-py`.
3. Have a Safe account configured with a threshold of 2, where two signatures are needed.

## Steps

### Install dependencies

`_10 yarn add @safe-global/api-kit @safe-global/protocol-kit @safe-global/types-kit`

### Imports

`_10 import SafeApiKit from '@safe-global/api-kit'_10 import Safe from '@safe-global/protocol-kit'_10 import {_10 MetaTransactionData,_10 OperationType_10 } from '@safe-global/types-kit'`

### Create a Safe transaction

`_18 // Initialize the Protocol Kit with Owner A_18 const protocolKitOwnerA = await Safe.init({_18 provider: config.RPC_URL,_18 signer: config.OWNER_A_PRIVATE_KEY,_18 safeAddress: config.SAFE_ADDRESS_18 })_18_18 // Create a Safe transaction_18 const safeTransactionData: MetaTransactionData = {_18 to: config.TO,_18 value: config.VALUE,_18 data: '0x',_18 operation: OperationType.Call_18 }_18_18 const safeTransaction = await protocolKitOwnerA.createTransaction({_18 transactions: [safeTransactionData]_18 })`

### Sign the transaction

`_10 // Sign the transaction with Owner A_10 const safeTxHash = await protocolKitOwnerA.getTransactionHash(safeTransaction)_10 const signatureOwnerA = await protocolKitOwnerA.signHash(safeTxHash)`

### Send the transaction to the service

`_15 // Initialize the API Kit_15 // How to get an Api key => http://docs.safe.global/core-api/how-to-use-api-keys_15 const apiKit = new SafeApiKit({_15 chainId: 11155111n,_15 apiKey: 'YOUR_API_KEY'_15 })_15_15 // Send the transaction to the Transaction Service with the signature from Owner A_15 await apiKit.proposeTransaction({_15 safeAddress: config.SAFE_ADDRESS,_15 safeTransactionData: safeTransaction.data,_15 safeTxHash,_15 senderAddress: config.OWNER_A_ADDRESS,_15 senderSignature: signatureOwnerA.data_15 })`

### Collect missing signatures

#### Get the pending transaction

`_10 const signedTransaction = await apiKit.getTransaction(safeTxHash)`

#### Add missing signatures

`_15 // Initialize the Protocol Kit with Owner B_15 const protocolKitOwnerB = await Safe.init({_15 provider: config.RPC_URL,_15 signer: config.OWNER_B_PRIVATE_KEY,_15 safeAddress: config.SAFE_ADDRESS_15 })_15_15 // Sign the transaction with Owner B_15 const signatureOwnerB = await protocolKitOwnerB.signHash(safeTxHash)_15_15 // Send the transaction to the Transaction Service with the signature from Owner B_15 await apiKit.confirmTransaction(_15 safeTxHash,_15 signatureOwnerB.data_15 )`

### Execute the transaction

`_10 const transactionResponse =_10 await protocolKitOwnerA.executeTransaction(signedTransaction)`

### Get the executed transaction

`_10 const transactions = await apiKit.getMultisigTransactions(config.SAFE_ADDRESS)_10_10 if (transactions.results.length > 0) {_10 console.log('Last executed transaction', transactions.results[0])_10 }`