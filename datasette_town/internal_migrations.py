from sqlite_utils import Database
from sqlite_migrate import Migrations

internal_migrations = Migrations("datasette-town.internal")


@internal_migrations()
def m001_initial(db: Database):
    db.executescript(
        """
        CREATE TABLE datasette_town_queries(
            id TEXT PRIMARY KEY,
            database_name TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            sql TEXT NOT NULL DEFAULT '',
            is_public INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
        );

        CREATE TABLE datasette_town_shares(
            id TEXT PRIMARY KEY,
            query_id TEXT NOT NULL REFERENCES datasette_town_queries(id) ON DELETE CASCADE,
            actor_id TEXT NOT NULL,
            can_edit INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
            UNIQUE(query_id, actor_id)
        );
        """
    )
