# https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-tables?view=sql-server-ver15

recommendations: true
manager: jroth
breadcrumb_path: ../../breadcrumb/toc.json
ms.update-cycle: 1825-days
description: System-versioned temporal tables bring built-in support for providing information about data stored in the table at any point in time.
author: rwestMSFT
ms.author: randolphwest
ms.date: 2025-05-19T00:00:00.0000000Z
ms.service: sql
ms.subservice: table-view-index
ms.topic: concept-article
ms.custom:
- ignite-2025
locale: en-us
document_id: 2f9c244b-870b-737f-6f6d-db9675179427

...

# Temporal Tables - SQL Server | Microsoft Learn
## What is a system-versioned temporal table?
A system-versioned temporal table is a type of user table designed to keep a full history of data changes, allowing easy point-in-time analysis. This type of temporal table is referred to as a system-versioned temporal table, because the system manages the period of validity for each row (that is, the Database Engine).
Every temporal table has two explicitly defined columns, each with a **datetime2** data type. These columns are referred to as *period* columns. These period columns are used exclusively by the system to record the period of validity for each row, whenever a row is modified. The main table that stores current data is referred to as the *current table*, or simply as the *temporal table*.
In addition to these period columns, a temporal table also contains a reference to another table with a mirrored schema, called the *history table*. The system uses the history table to automatically store the previous version of the row each time a row in the temporal table gets updated or deleted.
During temporal table creation, you can specify an existing history table (which must be schema compliant) or let the system create a default history table.

...

## How does temporal work?
System-versioning for a table is implemented as a pair of tables: a current table, and a history table. Within each of these tables, two extra **datetime2** columns are used to define the period of validity for each row:
- **Period start column**: The system records the start time for the row in this column, typically denoted as the `ValidFrom` column.
- **Period end column**: The system records the end time for the row in this column, typically denoted as the `ValidTo` column.
The current table contains the *current value* for each row. The history table contains each previous value (the *old version*) for each row, if any, and the start time and end time for the period for which it was valid.

...

```sql
CREATE TABLE dbo.Employee
(
    [EmployeeID] INT NOT NULL PRIMARY KEY CLUSTERED,
    [Name] NVARCHAR (100) NOT NULL,
    [Position] VARCHAR (100) NOT NULL,
    [Department] VARCHAR (100) NOT NULL,
    [Address] NVARCHAR (1024) NOT NULL,
    [AnnualSalary] DECIMAL (10, 2) NOT NULL,
    [ValidFrom] DATETIME2 GENERATED ALWAYS AS ROW START,
    [ValidTo] DATETIME2 GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
)
WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = dbo.EmployeeHistory));
```

...

- **Inserts:** The system sets the value for the `ValidFrom` column to the begin time of the current transaction (in the UTC time zone) based on the system clock and assigns the value for the `ValidTo` column to the maximum value of `9999-12-31`. This marks the row as open.
- **Updates:** The system stores the previous value of the row in the history table and sets the value for the `ValidTo` column to the begin time of the current transaction (in the UTC time zone) based on the system clock. This marks the row as closed, with a period recorded for which the row was valid.
In the current table, the row is updated with its new value and the system sets the value for the `ValidFrom` column to the begin time for the transaction (in the UTC time zone) based on the system clock. The value for the updated row in the current table for the `ValidTo` column remains the maximum value of `9999-12-31`.
- **Deletes:** The system stores the previous value of the row in the history table and sets the value for the `ValidTo` column to the begin time of the current transaction (in the UTC time zone) based on the system clock. This marks the row as closed, with a period recorded for which the previous row was valid. In the current table, the row is removed. Queries of the current table don't return this row.
Only queries that deal with history data return data for which a row is closed.
- **Merge:** The operation behaves exactly as if up to three statements (an `INSERT`, an `UPDATE`, and/or a `DELETE`) executed, depending on what is specified as actions in the `MERGE` statement.
The times recorded in the system **datetime2** columns are based on the begin time of the transaction itself. For example, all rows inserted within a single transaction have the same UTC time recorded in the column corresponding to the start of the `SYSTEM_TIME` period.

...

## How do I query temporal data?
`FOR SYSTEM_TIME` filters out rows that have a period of validity with zero duration (`ValidFrom = ValidTo`).
Those rows are generated if you perform multiple updates on the same primary key within the same transaction. In that case, temporal querying returns only row versions before the transactions, and current rows after the transactions.

...

| Expression | Qualifying rows | Note |
| `AS OF`*date_time* | `ValidFrom <=`*date_time*`AND ValidTo >`*date_time* | Returns a table with rows containing the values that were current at the specified point in time in the past. Internally, a union is performed between the temporal table and its history table. The results are filtered to return the values in the row that was valid at the point in time, specified by the *date_time* parameter. The value for a row is deemed valid if the *system_start_time_column_name* value is less than or equal to the *date_time* parameter value, and the *system_end_time_column_name* value is greater than the *date_time* parameter value. |