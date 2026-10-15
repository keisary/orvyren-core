# https://www.postgresql.org/docs/19/ddl-temporal-tables.html

[Documentation](https://www.postgresql.org/docs/ "Documentation") → [PostgreSQL 19](https://www.postgresql.org/docs/19/index.html)
Development Versions: [19](https://www.postgresql.org/docs/19/ddl-temporal-tables.html "PostgreSQL 19 - 5.7. Temporal Tables") / [devel](https://www.postgresql.org/docs/devel/ddl-temporal-tables.html "PostgreSQL devel - 5.7. Temporal Tables")
This documentation is for an unsupported version of PostgreSQL.
You may want to view the same page for the [current](https://www.postgresql.org/docs/current/ddl-temporal-tables.html "PostgreSQL  - 5.7. Temporal Tables") version, or one of the other supported versions listed above instead.

...

# 5.7. Temporal Tables #
_Temporal tables_ allow users to track different dimensions of history. _Application time_ tracks the history of a thing out in the world, and _system time_ tracks the history of the database itself. (A database that does both is also called _bitemporal_ .) This section describes how to express and manage such histories in temporal tables.

## 5.7.1. Application Time #
_Application time_ refers to a history of the entity described by a table. In a typical non-temporal table, there is a single row for each entity. In a temporal table, an entity may have multiple rows, as long as those rows describe non-overlapping periods from its history. Application time requires each row to have a start and end time, expressing when the row is applicable.
The following SQL creates a temporal table that can store application time:
```
CREATE TABLE products (
    product_no integer,
    price numeric,
    **valid_at daterange** 
);
```
Records in a temporal table can be imagined on a timeline, as in [Figure 5.1](https://www.postgresql.org/docs/19/ddl-temporal-tables.html "Figure 5.1. Application Time Example") . Here we show three records describing two products. Each record is a tuple with three attributes: the product number, the price, and the application time. So product 5 was first offered for a price of 5.00 starting January 1, 2020, but then became 8.00 starting January 1, 2022.
Its second record has no specified end time, indicating that it is true indefinitely, or for all future time. The last record shows that product 6 was introduced January 1, 2021 for 9.00, then canceled January 1, 2024.

...

```
 product_no | price |        valid_at
------------+-------+-------------------------
          5 |  5.00 | [2020-01-01,2022-01-01)
          5 |  8.00 | [2022-01-01,)
          6 |  9.00 | [2021-01-01,2024-01-01)
```
We show the application time using range-type notation, because it is stored as a single column (either a range or multirange). Ranges include their start point but exclude their end point. That way two adjacent ranges cover all points without overlapping. See [Section 8.17](https://www.postgresql.org/docs/19/rangetypes.html "8.17. Range Types") for more information about range types.
In principle, a table with application-time ranges/multiranges is equivalent to a table that stores application-time “ instants ” : one for each second, millisecond, nanosecond, or whatever finest granularity is available. But such a table would contain far too many rows, so ranges/multiranges offer an optimization to represent the same information in a compact form.
In addition, ranges and multiranges offer a more convenient interface for typical temporal operations, where records change infrequently enough that separate “ versions ” persist for extended periods of time.

### 5.7.1.1. Temporal Primary Keys and Unique Constraints #
A table with application time has a different concept of entity uniqueness than a non-temporal table. Temporal entity uniqueness can be enforced with a temporal primary key. A regular primary key has at least one column, all columns are `NOT NULL` , and the combined value of all columns is unique.
A temporal primary key also has at least one such column, but in addition it has a final column that is of a range type or multirange type that shows when the row is applicable. The regular parts of the key must be unique for any moment in time, but non-unique rows are allowed if their application time does not overlap.
The syntax to create a temporal primary key is as follows:
```
CREATE TABLE products (
    product_no integer,
    price numeric,
    valid_at daterange,
    **PRIMARY KEY (product_no, valid_at WITHOUT OVERLAPS)** 
);
```

[... middle omitted — see footer ...]


...

### 5.7.1.2. Temporal Foreign Keys #
```
CREATE TABLE variants (
  id         integer,
  product_no integer,
  name       text,
  valid_at   daterange,
  PRIMARY KEY (id, valid_at WITHOUT OVERLAPS),
  **FOREIGN KEY (product_no, PERIOD valid_at) REFERENCES products (product_no, PERIOD valid_at)** 
);
```
Note that the keyword `PERIOD` must be used for the application-time column in both the referencing and referenced table.
A temporal primary key or unique constraint matching the referenced columns must exist on the referenced table.

...

## 5.7.2. System Time [#
_System time_ refers to the history of the database table, not the entity it describes. It captures when each row was inserted/updated/deleted.
PostgreSQL does not currently support system time, but it could be emulated using triggers, and there are external extensions that provide such functionality.
| [Prev](https://www.postgresql.org/docs/19/ddl-system-columns.html "5.6. System Columns") | [Up](https://www.postgresql.org/docs/19/ddl.html "Chapter 5. Data Definition") | [Next](https://www.postgresql.org/docs/19/ddl-alter.html "5.8. Modifying Tables") |
| 5.6. System Columns | [Home](https://www.postgresql.org/docs/19/index.html "PostgreSQL 19beta4 Documentation") | 5.8. Modifying Tables |

──────── [TRUNCATED] ────────
Showing 4,403 chars (head) + 1,275 chars (tail) of 6,814 total clean characters.
Full text saved to: C:\Users\User\AppData\Local\hermes\cache\web\www.postgresql.org-85a7bbf5fb.md
To read the omitted middle: read_file path="C:\Users\User\AppData\Local\hermes\cache\web\www.postgresql.org-85a7bbf5fb.md" offset=49 limit=200  (the file is the complete page; raise/lower offset to page through it).
─────────────────────────────