from datasette.database import Database
from ulid import ULID


def ulid_new():
    return str(ULID()).lower()


_QUERY_COLUMNS = (
    "id, database_name, actor_id, title, description, sql, created_at, updated_at"
)


def _row_to_query(row) -> dict:
    return {
        "id": row[0],
        "database_name": row[1],
        "actor_id": row[2],
        "title": row[3],
        "description": row[4],
        "sql": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


class InternalDB:
    def __init__(self, internal_db: Database):
        self.db = internal_db

    async def create_query(
        self,
        database_name: str,
        actor_id: str,
        title: str,
        description: str,
        sql: str,
    ) -> str:
        def write(conn) -> str:
            with conn:
                query_id = ulid_new()
                conn.execute(
                    """
                    INSERT INTO datasette_town_queries(id, database_name, actor_id, title, description, sql)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [query_id, database_name, actor_id, title, description, sql],
                )
                return query_id

        return await self.db.execute_write_fn(write)

    async def get_query(self, query_id: str) -> dict | None:
        def read(conn):
            row = conn.execute(
                f"SELECT {_QUERY_COLUMNS} FROM datasette_town_queries WHERE id = ?",
                [query_id],
            ).fetchone()
            return _row_to_query(row) if row is not None else None

        return await self.db.execute_write_fn(read)

    async def update_query(self, query_id: str, title: str, description: str, sql: str):
        def write(conn):
            with conn:
                conn.execute(
                    """
                    UPDATE datasette_town_queries
                    SET title = ?, description = ?, sql = ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now')
                    WHERE id = ?
                    """,
                    [title, description, sql, query_id],
                )

        return await self.db.execute_write_fn(write)

    async def patch_query(self, query_id: str, **fields):
        """Update only the provided fields."""
        col_map = {
            "title": "title",
            "description": "description",
            "sql": "sql",
        }
        set_parts = []
        values = []
        for key, val in fields.items():
            if key not in col_map:
                continue
            set_parts.append(f"{col_map[key]} = ?")
            values.append(val)
        if not set_parts:
            return
        set_parts.append("updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now')")
        values.append(query_id)
        sql = f"UPDATE datasette_town_queries SET {', '.join(set_parts)} WHERE id = ?"

        def write(conn):
            with conn:
                conn.execute(sql, values)

        return await self.db.execute_write_fn(write)

    async def delete_query(self, query_id: str):
        def write(conn):
            with conn:
                conn.execute(
                    "DELETE FROM datasette_town_queries WHERE id = ?", [query_id]
                )

        return await self.db.execute_write_fn(write)

    async def list_queries_for_actor(
        self, database_name: str, actor_id: str
    ) -> list[dict]:
        def read(conn):
            rows = conn.execute(
                f"""
                SELECT {_QUERY_COLUMNS}
                FROM datasette_town_queries
                WHERE database_name = ? AND actor_id = ?
                ORDER BY updated_at DESC
                """,
                [database_name, actor_id],
            ).fetchall()
            return [_row_to_query(r) for r in rows]

        return await self.db.execute_write_fn(read)

    async def get_queries_by_ids(self, query_ids: list[str]) -> list[dict]:
        """Bulk-fetch queries by id, ordered by most recently updated.

        Used to materialize the set of query ids datasette-acl says an actor may
        view (see allowed_resources in the list page).
        """
        if not query_ids:
            return []

        def read(conn):
            placeholders = ",".join("?" for _ in query_ids)
            rows = conn.execute(
                f"""
                SELECT {_QUERY_COLUMNS}
                FROM datasette_town_queries
                WHERE id IN ({placeholders})
                ORDER BY updated_at DESC
                """,
                query_ids,
            ).fetchall()
            return [_row_to_query(r) for r in rows]

        return await self.db.execute_write_fn(read)
