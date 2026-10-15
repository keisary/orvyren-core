URL: https://github.com/llamaxyz/llama
TITLE: GitHub - llamaxyz/llama: Llama is an onchain governance and access control framework for smart contracts. · GitHub
ERR: None

# llamaxyz/llama
- Page: GitHub repository
- URL: https://github.com/llamaxyz/llama
- Description: Llama is an onchain governance and access control framework for smart contracts. - llamaxyz/llama
- License: MIT license
- Default branch: main
- Created: 2023-01-10T03:45:05.000Z
- Commits: 271

...

## README.md
[Llama](https://github.com/llamaxyz/llama/blob/main/.github/assets/llama-banner.png)
[CI](https://github.com/llamaxyz/llama/actions/workflows/ci.yml/badge.svg) [License: MIT](https://opensource.org/licenses/MIT)

# Llama
Llama is an onchain governance and access control framework for smart contracts. It uses non-transferable NFTs to encode access control, features programmatic control of funds, and includes modular strategies to define action execution rules.

...

## Setup
* The `MAINNET_RPC_URL` variable is the only one that is required for running tests.
* You may also want a mainnet `ETHERSCAN_API_KEY` for better traces when running fork tests.
* The rest are only needed for deployment verification with forge scripts. An anvil default private key is provided in the `.env.example` file to facilitate testing.

...

## Testnet deployments
| Name | Sepolia | Holesky | Base Sepolia |
| _Factory_ |  |  |  |
| LlamaFactory | [0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB](https://sepolia.etherscan.io/address/0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB) | [0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB](https://holesky.etherscan.io/address/0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB) | [0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB](https://sepolia.basescan.org/address/0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB) |
| _Main instance contracts_ |  |  |  |
| LlamaPolicyMetadata (logic contract) | [0xf2C61E275d48efA8a6556529F60cE1E376510e0F](https://sepolia.etherscan.io/address/0xf2C61E275d48efA8a6556529F60cE1E376510e0F) | [0xf2C61E275d48efA8a6556529F60cE1E376510e0F](https://holesky.etherscan.io/address/0xf2C61E275d48efA8a6556529F60cE1E376510e0F) | [0xf2C61E275d48efA8a6556529F60cE1E376510e0F](https://sepolia.basescan.org/address/0xf2C61E275d48efA8a6556529F60cE1E376510e0F) |
| _Strategy logic contracts_ |  |  |  |

...

| Name | Sepolia | Holesky | Base Sepolia |
| _Factory_ |  |  |  |
| LlamaFactory | [0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB](https://sepolia.etherscan.io/address/0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB) | [0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB](https://holesky.etherscan.io/address/0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB) | [0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB](https://sepolia.basescan.org/address/0xFf5d4E226D9A3496EECE31083a8F493edd79AbEB) |
| _Main instance contracts_ |  |  |  |
| LlamaAbsolutePeerReview | [0x0092CD4044E1672c9c513867eb75e6213AF9742f](https://sepolia.etherscan.io/address/0x0092CD4044E1672c9c513867eb75e6213AF9742f) | [0x0092CD4044E1672c9c513867eb75e6213AF9742f](https://holesky.etherscan.io/address/0x0092CD4044E1672c9c513867eb75e6213AF9742f) | [0x0092CD4044E1672c9c513867eb75e6213AF9742f](https://sepolia.basescan.org/address/0x0092CD4044E1672c9c513867eb75e6213AF9742f) |
| _Account logic contracts_ |  |  |  |

...

## Documentation
To read all of our documentation, visit [https://docs.llama.xyz](https://docs.llama.xyz/) . To view Llama framework documentation only, visit the [docs directory](https://github.com/llamaxyz/llama/tree/main/docs) .

### Smart contract reference
Run the following command to generate smart contract reference documentation from our NatSpec comments and serve those static files locally:
```shell
$ forge doc -o reference/ -b -s
```