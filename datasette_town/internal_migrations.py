from sqlite_utils import Database
from sqlite_migrate import Migrations

internal_migrations = Migrations("datasette-town.internal")


@internal_migrations()
def m001_initial(db: Database):
    # Per-query access (view / edit / manage, including public access and
    # sharing with people and groups) is owned by datasette-acl. The creator is
    # recorded in actor_id and seeded a Manager grant on create. There is no
    # shares table or is_public column — both are acl grants now.
    db.executescript(
        """
        CREATE TABLE datasette_town_queries(
            id TEXT PRIMARY KEY,
            database_name TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            sql TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
        );
        """
    )
