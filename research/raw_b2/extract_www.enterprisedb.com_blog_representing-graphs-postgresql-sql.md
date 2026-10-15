# https://www.enterprisedb.com/blog/representing-graphs-postgresql-sqlpgq

# Representing graphs in PostgreSQL with SQL/PGQ

 February 18, 2025

As a huge fan of Tolkien and graph theory, [this excellent blog post](https://www.richard-towers.com/2025/02/16/representing-graphs-in-postgres.html) shared by my colleagues at EDB piqued my interest.

The author describes how a graph can be modeled in PostgreSQL and recursive CTEs can be used to execute graph-traversal queries and concludes:

> This is one way of representing graph-like data in Postgresql, and querying it in a flexible way.
>
> I’d be very interested in hearing about other techniques or improvements.

And indeed there *is* a new technique under development for natively working with graphs in Postgres!

## SQL Property Graph Queries

SQL Property Graph Queries (SQL/PGQ) are now part of the [SQL:2023](https://peter.eisentraut.org/blog/2023/04/04/sql-2023-is-finished-here-is-whats-new) ISO standard and provide the ability to efficiently represent and query existing relational data as a graph without requiring a separate graph database management system (such as Neo4j).

Representing relationships between nodes through connected edges is a very natural and useful ability which is particularly well-suited for representing networks— social networks [of friends of friends](https://en.wikipedia.org/wiki/Six_degrees_of_separation), transportation networks, computer networks and more.

## Adding this Power to Postgres!

While there are third-party extensions which add graph database functionality to Postgres, such as [Apache AGE™](https://age.apache.org/overview), discussion and work to implement SQL/PGQ into Postgres has been ongoing by contributors in the [pgsql-hackers](https://www.postgresql.org/message-id/flat/CAEG8a3L3uZZRT5Ra5%3D9G-SOCEYULejw5eqQE99VL0YfTeX3-BA%40mail.gmail.com#f477d33034dd8df626c0cfdad4e9e085) mailing list.

While still very much a work-in-progress with no release date, it is functional and can be patched into Postgres for you to explore!

### Patching in three easy steps

Applying these patches requires that Postgres is built and installed from the source code. The [Postgres documentation](https://www.postgresql.org/docs/current/installation.html) provides a comprehensive overview on the topic.

1. Download all **.patch** files from this [psql-hackers thread](https://www.postgresql.org/message-id/flat/CAEG8a3L3uZZRT5Ra5%3D9G-SOCEYULejw5eqQE99VL0YfTeX3-BA%40mail.gmail.com#f477d33034dd8df626c0cfdad4e9e085)
2. Get the Postgres source code (see [https://www.postgresql.org/docs/current/install-getsource.html](https://www.postgresql.org/docs/current/install-getsource.html)), then change into the directory that contains the Postgres source code for the rest of the installation procedure
3. For each **.patch** file downloaded (mine downloaded under the **Downloads** directory on Debian 12), run

```bash
patch -p1 < ~/Downloads/v10-00NN-x-y-z.patch
```

Replacing **NN-x-y-z** with the appropriate patch file name.

Once all the patches are applied, we are ready to build and install SQL/PGQ-patched Postgres!

### Building and Installing

NOTE: Before running **./configure**, ensure the required tools are installed (on a Debian 12 OS, I had to install **libicu-dev**, **bison** and **flex**).

The [short version](https://www.postgresql.org/docs/current/install-make.html#INSTALL-SHORT-MAKE) should suffice for building and installing Postgres, but build it according to your needs.

```bash
./configure
make
su
make install
adduser postgres
mkdir -p /usr/local/pgsql/data
chown postgres /usr/local/pgsql/data
su - postgres
/usr/local/pgsql/bin/initdb -D /usr/local/pgsql/data
/usr/local/pgsql/bin/pg_ctl -D /usr/local/pgsql/data -l logfile start
/usr/local/pgsql/bin/createdb test
/usr/local/pgsql/bin/psql test
```

## Graphs in Action!

The [blog post](https://www.richard-towers.com/2025/02/16/representing-graphs-in-postgres.html) which inspired this post uses Tolkien characters as example data; we will create the same data and demonstrate query parity using SQL/PGQ methods.

### Creating tables

First, fire up **psql** and generate two tables; one for characters (**nodes**) and one for relationships (**edges**):

```sql
CREATE TABLE nodes (
 id SERIAL PRIMARY KEY,
 name TEXT,
 details JSONB
);
CREATE TABLE edges (
 id SERIAL PRIMARY KEY,
 type TEXT,
 from_id INTEGER REFERENCES nodes(id),
 to_id INTEGER REFERENCES nodes(id),
 details JSONB
);
```

### Creating data

Next, populate these tables with data:

```sql
INSERT INTO nodes (name, details) VALUES
 ('Frodo Baggins', '{"species": "Hobbit"}'), -- 1
 ('Bilbo Baggins', '{"species": "Hobbit"}'), -- 2
 ('Samwise Gamgee', '{"species": "Hobbit"}'), -- 3
 ('Hamfast Gamgee', '{"species": "Hobbit"}'), -- 4
 ('Gandalf', '{"species": "Wizard"}'), -- 5
 ('Aragorn', '{"species": "Human"}'), -- 6
 ('Arathorn', '{"species": "Human"}'), -- 7
 ('Legolas', '{"species": "Elf"}'), -- 8
 ('Thranduil', '{"species": "Elf"}'), -- 9
 ('Gimli', '{"species": "Dwarf"}'), -- 10
 ('Gloin', '{"species": "Dwarf"}'); -- 11
-- Parents
INSERT INTO edges (type, from_id, to_id, details) VALUES
 ('parent', 2, 1, '{}'),
 ('parent', 4, 3, '{}'),
 ('parent', 7, 6, '{}'),
 ('parent', 9, 8, '{}'),
 ('parent', 11, 10, '{}');
```

### Creating a Property Graph


[... middle omitted — see footer ...]

 MATCH (a IS node WHERE a.name='Samwise Gamgee')-[x IS relationship WHERE x.type='friend']->(b IS node)-[y IS relationship WHERE y.type='friend']->(c IS node)<-[z IS relationship WHERE z.type='parent']-(d IS node)
 COLUMNS (d.id, d.name as fof_parents, d.details as details)
);
```

The shape of the arrow in the MATCH statement neatly describes the graph traversal:

```sql
(Samwise Gamgee) -[friendship]-> (friend) -[friendship]-> (friend-of-friend) <-[parent]-(parent-of-friend-of-friend)
```

We traverse across all 'friend' relationship edges connected to Samwise Gamgee two levels away to find all friend-of-friends nodes and (like our first example, note the leftward arrow) look for the parent of each friend-of-friend node.

The query results are the same as the original blog post

```sql
id |  fof_parents   |        details
----+----------------+-----------------------
 2 | Bilbo Baggins  | {"species": "Hobbit"}
 4 | Hamfast Gamgee | {"species": "Hobbit"}
 7 | Arathorn       | {"species": "Human"}
 9 | Thranduil      | {"species": "Elf"}
11 | Gloin          | {"species": "Dwarf"}
(5 rows)
```

## Conclusion

SQL/PGQ provides a neat interface for working with graph-like data directly in PostgreSQL that is flexible, powerful and intuitive to read! These examples barely scratch the surface, but do show parity with the results of the reference blog post and present another technique for working with graphs in Postgres. It does not yet have a release date and this post demonstrates work-in-progress functionality, but I look forward to this exciting feature gaining full support in a future release of Postgres!

Thank you to all the pgsql-hackers whose hard work and cooperation makes this possible.

──────── [TRUNCATED] ────────
Showing 5,249 chars (head) + 1,720 chars (tail) of 14,067 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\www.enterprisedb.com-3de5dd6176.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\www.enterprisedb.com-3de5dd6176.md" offset=115 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────