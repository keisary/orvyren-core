# https://dialecticgroup.substack.com/p/introducing-nebula-a-graph-based

# Introducing Nebula: A graph based representation of DeFi
Original Publication by Ogst • March 26, 2024
In this series of blog posts, from the perspective of an institutional yield farming fund, we argue that DeFi should be represented as a knowledge graph to properly assess the risk of the available opportunities. Moreover, we compare this approach with similar work performed in other domains such as cybersecurity.

...

# **Introduction**
For better or worse, for the foreseeable future, the financial use-case is crypto’s killer app. Outside of speculation and decentralized capital formation, the financial use-case is dominated by DeFi. In the realm of DeFi, the concept of “being finance legos” underscores the emergence of intricate structures characterized by numerous interdependencies.

...

In summary, navigating the complexities of DeFi requires a comprehensive grasp of protocol dependencies and a meticulous approach to due diligence. By understanding these interconnections, participants can better assess and mitigate risks in the ever-evolving landscape of DeFi.
**DeFi as a graph**
To alleviate the aforementioned concerns and streamline the process of due diligence and risk scoring, we propose the introduction of the DeFi Graph, which models dependencies within the DeFi ecosystem.
Opting for a knowledge graph structure instead of tables and join operations is primarily motivated by the uncertainty surrounding the length of dependency paths.

...

## **Graph construction**
As mentioned in the introduction, we consider the graph representation problem from the perspective of an institutional yield fund providing liquidity to various DeFi pools, which is Dialectic’s core focus. Thus, we center the graph around liquidity pools. In that knowledge graph, we represent the following nodes and edges to respectively document DeFi entities and relationships linking them :

...

This graph is built automatically using on chain data and NEO4J graph database. NEO4J also allows us to easily introduce new edges to document our crypto native teams knowledge about DeFi. It is important to note that the graph has been specifically generated to cater to the requirements of a yield farming fund focused on stable and ETH-related pools.

## **Results and implications**
The graph is populated based on our internal pool database consisting exclusively of Stablecoins (ex: DAI/USDT), and ETH/LST (ex: WETH/rETH) pools. We obtained a total of **5336** nodes and **14626** edges, detailed below:

...

# **Conclusion**
## Discussion about this post
Comments Restacks
Top Latest Discussions
No posts