# https://www.cybertec-postgresql.com/en/implementing-as-of-queries-in-postgresql/

# Implementing “AS OF”-queries in PostgreSQL
## Implementing “AS OF” and timetravel in user land
### Attention!
If you are looking for more information about this feature consider checking out the official documentation (https://www.postgresql.org/docs/current/ddl-constraints.html).

...

### How can I filter?
If you are running an application you usually don't care what is going on behind the scenes - you simply want to modify a table and things should take care of themselves in an easy way. Therefore, it makes sense to add a trigger to your t_object_current table, which takes care of versioning. Here is an example:

...

CREATE FUNCTION version_trigger() RETURNS trigger AS
$
BEGIN
IF TG_OP = 'UPDATE'
THEN
IF NEW.id <> OLD.id
THEN
RAISE EXCEPTION 'the ID must not be changed';
END IF;
UPDATE t_object
SET valid = tstzrange(lower(valid), current_timestamp)
WHERE id = NEW.id
AND current_timestamp <@ valid;
IF NOT FOUND THEN
RETURN NULL;
END IF;
END IF;
IF TG_OP IN ('INSERT', 'UPDATE')
THEN
INSERT INTO t_object (id, valid, some_data1, some_data2)
VALUES (NEW.id,

...

## Finally: Timetravel made easy
### 8 comments on “Implementing “AS OF”-queries in PostgreSQL”
1. **Ravi Krishna** says:
[February 5, 2019 at 3:35 pm](https://www.cybertec-postgresql.com/en/implementing-as-of-queries-in-postgresql/)
"Oracle has provided this kind of functionality for quite some time already"
Also DB2 LUW. DB2's implementation of bi temporal tables is probably the best.
Reply
2. **Дмитрий Долгов** says: