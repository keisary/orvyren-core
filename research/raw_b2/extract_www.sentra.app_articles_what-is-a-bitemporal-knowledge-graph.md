# https://www.sentra.app/articles/what-is-a-bitemporal-knowledge-graph

# What Is a Bi-Temporal Knowledge Graph? (and Why AI Memory Needs One)
## What "Bi-Temporal" Actually Means
A bi-temporal data model tracks two independent kinds of time for every fact it stores. Valid time is the period during which a fact is true in the real world. Transaction time is when the system actually recorded that fact. The terms come from Richard Snodgrass and are codified in the SQL:2011 standard.

...

## How Sentra Implements Bi-Temporal Memory
Sentra builds the principles above into a working memory layer that sits beneath your agents, not beside them. The design choice that defines it is write-time comprehension. Sentra resolves what a fact means at the moment it arrives, against a per-organization ontology, rather than rediscovering meaning on every query. Vector-based RAG works the other way around.
It stores embeddings at write time, then guesses structure when an agent queries, so every request crawls Slack, email, and docs to figure out what something means again.
That difference changes how time gets handled. When a new fact contradicts an old one, Sentra invalidates the old fact instead of deleting it. Each fact carries both a valid time and a stop time, so an agent can ask what is true now and what was true in March and get two different, correct answers. Provenance stays first-class, which means the system can always show where a fact came from and when it changed.
The benchmark numbers measure whether that design actually holds. On the MEME benchmark (KAIST, 2026), Sentra scores 40% on Cascade and 43% on Absence, against field averages of 3% and 1%. Those two tasks test exactly the behavior bi-temporal structure exists to support, tracking how a fact propagates after it changes and recognizing when something is no longer true. Sentra is the only system above 30% on both.
The shared-layer claim rests on reach, not just structure. Sentra connects to 200+ tools through REST or MCP, including HubSpot, Gmail, Slack, GitHub, Notion, and Linear. One graph reads from all of them and serves humans and every agent from the same source, so a correction made once propagates everywhere instead of living inside one model's session.