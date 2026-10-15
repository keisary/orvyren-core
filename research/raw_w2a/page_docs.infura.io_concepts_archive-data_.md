For AI agents: a documentation index is available at [/llms.txt](https://docs.infura.io/llms.txt). A markdown version of this page is available at the same URL with .md appended (or via Accept: text/markdown).

[Skip to main content](https://docs.infura.io/concepts/archive-data#__docusaurus_skipToContent_fallback)

On this page

Archive data is data on the blockchain that is older than 128 blocks.

important

For users on [Infura's credit pricing plan](https://docs.infura.io/get-started/pricing/), requests for
archive data currently cost the same as non-archive data, but this might change in the future.

## Infura-supported archive data [​](https://docs.infura.io/concepts/archive-data\#infura-supported-archive-data "Direct link to Infura-supported archive data")

Access to archive data is automatically enabled on the following supported networks:

| Mainnet | Testnet |
| --- | --- |
| Ethereum | Sepolia |
| Optimism | Sepolia |
| Polygon | Amoy |
| Arbitrum |  |
| Celo |  |
| Sei |  |

Infura provides access to [full nodes](https://docs.infura.io/concepts/archive-data#full-nodes)
and [archive nodes](https://docs.infura.io/concepts/archive-data#archive-nodes).

## Full nodes [​](https://docs.infura.io/concepts/archive-data\#full-nodes "Direct link to Full nodes")

Full nodes maintain the current state of the blockchain and are responsible for providing data on request and executing smart contract transactions.

Full nodes store enough data to recalculate the chain in the event of a chain reorg. Beyond that, full nodes prune their data; only storing the data required for verifying transactions older than 128 blocks.

Pruning conserves disk space and helps with node sync time, thus reducing storage and computation costs. However, a pruned node cannot serve API requests for certain RPC methods older than 128 blocks.

## Archive nodes [​](https://docs.infura.io/concepts/archive-data\#archive-nodes "Direct link to Archive nodes")

Data older than 128 blocks are stored on archive nodes on the blockchain. These are full nodes running in archive mode.

Only an archive node can serve API requests for certain RPC methods older than 128 blocks. The Ethereum JSON-RPC and Websocket APIs include several methods which require access to an archive node.

## Methods requiring archive data [​](https://docs.infura.io/concepts/archive-data\#methods-requiring-archive-data "Direct link to Methods requiring archive data")

Requests for data older than the most recent 128 blocks require access to archive data.

The following methods include a parameter for specifying a block number for the request.

- `eth_getBalance`
- `eth_getCode`
- `eth_getTransactionCount`
- `eth_getStorageAt`
- `eth_call`

- [Infura-supported archive data](https://docs.infura.io/concepts/archive-data#infura-supported-archive-data)
- [Full nodes](https://docs.infura.io/concepts/archive-data#full-nodes)
- [Archive nodes](https://docs.infura.io/concepts/archive-data#archive-nodes)
- [Methods requiring archive data](https://docs.infura.io/concepts/archive-data#methods-requiring-archive-data)