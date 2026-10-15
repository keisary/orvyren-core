# https://gdotv.com/blog/kuzu-legacy-embedded-graph-database-landscape/

# Kuzu’s Legacy and the New Wave of Embedded Graph Databases

![Tech feature — Kuzu’s Legacy, and the Future of Embedded Graph Databases, on the gdotv blog](/_astro/kuzu-legacy-embedded-graph-database-landscape-gdotv.DhEUfNoG_ZQ0FdO.webp)

## Introduction

On October 10th, 2025, Kuzu’s GitHub repository was archived without warning. Four months later, [a European Commission filing](/blog/weekly-edge-kuzu-acquisition-apple-s3-graph-analytics-neo4j-vs-postgresql/) confirmed what most of the community had suspected: Apple had acqui-hired the team. [The Verge](https://www.theverge.com/tech/877360/apple-quietly-acquired-the-graph-database-company-kuzu-late-last-year) (and many other outlets) ran the story. We won’t speculate on the future of Kuzu under Apple, but we can reflect on the history of the project, and the landscape it helped build for embedded graph databases.

Here’s a non-exhaustive list of embedded graph databases that share some similarity with Kuzu:

| Project | Relationship to Kuzu | Standout property | Status (May 2026) |
|---|---|---|---|
| LadybugDB | Community fork; gdotv’s pick to carry Kuzu forward | Active roadmap; stewardship by Arun Sharma | Actively developed |
| Lance Graph | Spiritual heir; Prashanth Rao (ex-Kuzu) at LanceDB | Graph workloads on the Lance columnar format | Active development inside LanceDB |
| Raphtory | Pre-dates Kuzu; same embedded ethos | Temporal and persistent graph as a first-class concept | Mature, actively developed |
| TuringDB | Same embedded ethos | Versioning as a first-class concept | Active development |
| FalkorDBLite | Same embedded ethos | Multiple graphs per database, Python-first | Active development |

The rest of this post explains each entry, what it inherits from Kuzu, and where the gaps are.

## What is Kuzu

In short, Kuzu is an embedded graph database that uses columnar storage (and other techniques) to deliver high-performance graph analytical workloads as scale.

It’s a university spin-out project from the [Data Systems Group at the University of Waterloo](https://uwaterloo.ca/data-systems-group/), led by Semih Salihoğlu with a broader founding team drawn from the same lab.

The project was [introduced at CIDR 2023](https://www.cidrdb.org/cidr2023/papers/p48-jin.pdf), with follow-up research on graph learning applications [in openreview](https://openreview.net/forum?id=Eg3MthXzeT) and on join algorithms in the [ACM GRADES-NDA proceedings](https://dl.acm.org/doi/10.1145/3631504.3631514). Kuzu’s strong academic foundation made it a truly bleeding-edge database project.

Kuzu has published several research papers over the years that laid the foundation of their database architecture:

- **Vectorized and factorized query processing.** [Kuzu](https://github.com/kuzudb/kuzu) was a vectorized and factorized query processor. Factorization lets the engine represent intermediate results in compressed form rather than materializing every row, which is the load-bearing choice for analytical workloads.
- **Columnar sparse row (CSR) adjacency lists.** Kuzu used columnar sparse row-based (CSR) adjacency lists for its join indices. The choice has aged well. [pgGraph](https://github.com/Evokoa/pgGraph), a Postgres extension launched in 2025, describes its own storage as “O(1) adjacency via CSR”, with `graph.build()` compiling relationships into “forward and reverse compressed sparse row (CSR) edge stores”. Two projects, two slightly different framings of the same data structure. Convergent evolution in graph engine design.
- **Novel join algorithms.** Kuzu’s join algorithms drew on worst-case-optimal join research from the same Waterloo lab, documented in the papers above.
The Kuzu team turned their theories to practice, and went from an ambitious research effort to a genuine challenger in the graph database industry.

## The DuckDB of graph databases

The community gave Kuzu the nickname “the DuckDB of graph databases” early on. Kuzu deliberately aligned with what made DuckDB succeed, and adapted it to the constraints of graph workloads. The parallels are clear:

| Property | DuckDB | Kuzu |
|---|---|---|
| Written in C++ | ✓ | ✓ |
| Embedded, in-process execution | ✓ | ✓ |
| Single-file storage | ✓ | ✓ (since v0.11.0) |
| Native Parquet / Arrow / CSV / JSON ingestion | ✓ | ✓ |
| Attach extensions for external databases | ✓ | ✓ |
| WebAssembly bindings | ✓ (duckdb-wasm) | ✓ (kuzu-wasm) |

The detail on each:

**Embedded, in-process execution.** DuckDB describes itself as a database that [“does not run as a separate process, but completely embedded within a host process”](https://duckdb.org/why_duckdb). Kuzu took the same shape: embeddable and serverless, no service to deploy, no network hop, the database lives in the same process as your code.

**Single-file storage.** DuckDB’s native format is, per the same page, “a single-file database”. Kuzu moved to the same model in [v0.11.0](https://github.com/kuzudb/kuzu/releases/tag/v0.11.0), consolidating its previous multi-file directory into a single `data.kz` artifact. The portability story is what you would expect: drop the file next to your code, ship it via object storage like AWS S3, mount it into a container, version it, hand it to a colleague.

**Native multi-format ingestion.** DuckDB reads [Parquet](https://duckdb.org/docs/stable/data/parquet/overview), CSV, JSON, and Arrow data efficiently as a first-class concern. Kuzu adopted the same posture, reading Parquet, Arrow, CSV, and JSON natively without an ETL step.


[... middle omitted — see footer ...]


Kuzu’s exit raises a difficult question: how can successful open source databases achieve durable governance and commercial sustainability? This applies to open source in general, and it’s a known challenge that Kuzu gave a reminder of. Kuzu’s commercial strategy was opaque enough that the archival caught most of its users by surprise. The successor projects are aware of this, and the open governance and permissive licensing posture they have adopted is a direct response. Whether that posture survives contact with the same commercial pressures remains to be seen.

Independent of where the team ended up, Kuzu changed what people expected from a graph database. The combination of embedded execution, columnar storage, Cypher, and single-file portability is no longer just a nice to have. Kuzu raised the bar for the industry, and that is their true legacy. The successors above are not Kuzu, but they exist because Kuzu showed what was possible, and that is more than most projects manage in the time they get.

If you are working with LadybugDB and want a graph IDE alongside it, [gdotv is ready](/databases/ladybugdb/).

## Our solutions

Whether you're an individual or part of a larger team, there's a version of gdotv that's right for you.

### [gdotv Desktop](/products/gdotv-desktop/)

The ultimate graph database IDE.

Install and connect your first graph database in 2 minutes.

### [gdotv Team](/products/gdotv-team/)

The unified workbench for graph data teams.

Deploy to your team in under 15 minutes. Marketplace or self-hosted.

### [gdotv Enterprise](/products/gdotv-enterprise/)

The universal graph intelligence platform.

For organization-wide deployments. Bring graph data directly to your analysts.

──────── [TRUNCATED] ────────
Showing 5,522 chars (head) + 1,727 chars (tail) of 17,315 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\gdotv.com-a430f6b928.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\gdotv.com-a430f6b928.md" offset=57 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────