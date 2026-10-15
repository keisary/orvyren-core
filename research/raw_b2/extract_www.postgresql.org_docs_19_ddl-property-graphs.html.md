# https://www.postgresql.org/docs/19/ddl-property-graphs.html

# PostgreSQL: Documentation: 19: 5.15.Â Property Graphs
URL: https://www.postgresql.org/docs/19/ddl-property-graphs.html
Published: 2026-08-13

PostgreSQL: Documentation: 19: 5.15. Property Graphs

August 13, 2026: PostgreSQL 18.6, 17.11, 16.15, 15.19, 14.24 and 19 Beta 3 Released!

Documentationâ PostgreSQL 19

Development Versions: 19/ devel

This documentation is for an unsupported version of PostgreSQL. You may want to view the same page for the current version, or one of the other supported versions listed above instead.

| 5.15. Property Graphs | | | | |
| --- | --- | --- | --- | --- |
| Prev | Up | Chapter 5. Data Definition | Home | Next |

---

## 5.15. Property Graphs #

A property graph is a way to represent database contents, as an alternative to the usual (in SQL) approach of representing database contents using relational structures such as tables. A property graph can then be queried using graph pattern matching syntax, instead of join queries typical of relational databases. PostgreSQL implements SQL/PGQ[6], which is part of the SQL standard, where a property graph is defined as a kind of read-only view over relational tables. So the actual data is still in tables or table-like objects, but is exposed as a graph for graph querying operations. (This is in contrast to native graph databases, where the data is stored directly in a graph structure.) Underneath, both relational queries and graph queries use the same query planning and execution infrastructure, and in fact relational and graph queries can be combined and mixed in single queries.

A graph is a set of vertices and edges. Each edge has two distinguishable associated vertices called the source and destination vertices. (So in this model, all edges are directed.) Vertices and edges together are called the elements of the graph. A property graph extends this well-known mathematical structure with a way to represent user data. In a property graph, each vertex or edge has one or more associated labels, and each label has zero or more properties. The labels are similar to table row types in that they define the kind of the contained data and its structure. The properties are similar to columns in that they contain the actual data. In fact, by default, a property graph definition exposes the underlying tables and columns as labels and properties, but more complicated definitions are possible.

Consider the following table definitions:

```

CREATE TABLE products (
    product_no integer PRIMARY KEY,
    name varchar,
    price numeric
);

CREATE TABLE customers (
    customer_id integer PRIMARY KEY,
    name varchar,
    address varchar
);

CREATE TABLE orders (
    order_id integer PRIMARY KEY,
    ordered_when date
);

CREATE TABLE order_items (
    order_items_id integer PRIMARY KEY,
    order_id integer REFERENCES orders (order_id),
    product_no integer REFERENCES products (product_no),
    quantity integer
);

CREATE TABLE customer_orders (
    customer_orders_id integer PRIMARY KEY,
    customer_id integer REFERENCES customers (customer_id),
    order_id integer REFERENCES orders (order_id)
);

```

When mapping