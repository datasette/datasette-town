from datasette.database import Database
from ulid import ULID


def ulid_new():
    return str(ULID()).lower()


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
        is_public: bool,
    ) -> str:
        def write(conn) -> str:
            with conn:
                query_id = ulid_new()
                conn.execute(
                    """
                    INSERT INTO datasette_town_queries(id, database_name, actor_id, title, description, sql, is_public)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        query_id,
                        database_name,
                        actor_id,
                        title,
                        description,
                        sql,
                        int(is_public),
                    ],
                )
                return query_id

        return await self.db.execute_write_fn(write)

    async def get_query(self, query_id: str) -> dict | None:
        def read(conn):
            row = conn.execute(
                "SELECT id, database_name, actor_id, title, description, sql, is_public, created_at, updated_at"
                " FROM datasette_town_queries WHERE id = ?",
                [query_id],
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "database_name": row[1],
                "actor_id": row[2],
                "title": row[3],
                "description": row[4],
                "sql": row[5],
                "is_public": bool(row[6]),
                "created_at": row[7],
                "updated_at": row[8],
            }

        return await self.db.execute_write_fn(read)

    async def update_query(
        self, query_id: str, title: str, description: str, sql: str, is_public: bool
    ):
        def write(conn):
            with conn:
                conn.execute(
                    """
                    UPDATE datasette_town_queries
                    SET title = ?, description = ?, sql = ?, is_public = ?,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now')
                    WHERE id = ?
                    """,
                    [title, description, sql, int(is_public), query_id],
                )

        return await self.db.execute_write_fn(write)

    async def patch_query(self, query_id: str, **fields):
        """Update only the provided fields."""
        if not fields:
            return
        col_map = {
            "title": "title",
            "description": "description",
            "sql": "sql",
            "is_public": "is_public",
        }
        set_parts = []
        values = []
        for key, val in fields.items():
            if key not in col_map:
                continue
            set_parts.append(f"{col_map[key]} = ?")
            values.append(int(val) if key == "is_public" else val)
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
                    "DELETE FROM datasette_town_shares WHERE query_id = ?", [query_id]
                )
                conn.execute(
                    "DELETE FROM datasette_town_queries WHERE id = ?", [query_id]
                )

        return await self.db.execute_write_fn(write)

    async def list_queries_for_actor(
        self, database_name: str, actor_id: str
    ) -> list[dict]:
        def read(conn):
            rows = conn.execute(
                """
                SELECT id, database_name, actor_id, title, description, sql, is_public, created_at, updated_at
                FROM datasette_town_queries
                WHERE database_name = ? AND actor_id = ?
                ORDER BY updated_at DESC
                """,
                [database_name, actor_id],
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "database_name": r[1],
                    "actor_id": r[2],
                    "title": r[3],
                    "description": r[4],
                    "sql": r[5],
                    "is_public": bool(r[6]),
                    "created_at": r[7],
                    "updated_at": r[8],
                }
                for r in rows
            ]

        return await self.db.execute_write_fn(read)

    async def list_shared_queries_for_actor(
        self, database_name: str, actor_id: str
    ) -> list[dict]:
        def read(conn):
            rows = conn.execute(
                """
                SELECT q.id, q.database_name, q.actor_id, q.title, q.description, q.sql,
                       q.is_public, q.created_at, q.updated_at, s.can_edit
                FROM datasette_town_queries q
                JOIN datasette_town_shares s ON s.query_id = q.id
                WHERE q.database_name = ? AND s.actor_id = ?
                ORDER BY q.updated_at DESC
                """,
                [database_name, actor_id],
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "database_name": r[1],
                    "actor_id": r[2],
                    "title": r[3],
                    "description": r[4],
                    "sql": r[5],
                    "is_public": bool(r[6]),
                    "created_at": r[7],
                    "updated_at": r[8],
                    "can_edit": bool(r[9]),
                }
                for r in rows
            ]

        return await self.db.execute_write_fn(read)

    async def list_public_queries(self, database_name: str) -> list[dict]:
        def read(conn):
            rows = conn.execute(
                """
                SELECT id, database_name, actor_id, title, description, sql, is_public, created_at, updated_at
                FROM datasette_town_queries
                WHERE database_name = ? AND is_public = 1
                ORDER BY updated_at DESC
                """,
                [database_name],
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "database_name": r[1],
                    "actor_id": r[2],
                    "title": r[3],
                    "description": r[4],
                    "sql": r[5],
                    "is_public": bool(r[6]),
                    "created_at": r[7],
                    "updated_at": r[8],
                }
                for r in rows
            ]

        return await self.db.execute_write_fn(read)

    async def add_share(self, query_id: str, actor_id: str, can_edit: bool) -> str:
        def write(conn) -> str:
            with conn:
                share_id = ulid_new()
                conn.execute(
                    """
                    INSERT INTO datasette_town_shares(id, query_id, actor_id, can_edit)
                    VALUES (?, ?, ?, ?)
                    """,
                    [share_id, query_id, actor_id, int(can_edit)],
                )
                return share_id

        return await self.db.execute_write_fn(write)

    async def remove_share(self, share_id: str):
        def write(conn):
            with conn:
                conn.execute(
                    "DELETE FROM datasette_town_shares WHERE id = ?", [share_id]
                )

        return await self.db.execute_write_fn(write)

    async def update_share(self, share_id: str, can_edit: bool):
        def write(conn):
            with conn:
                conn.execute(
                    "UPDATE datasette_town_shares SET can_edit = ? WHERE id = ?",
                    [int(can_edit), share_id],
                )

        return await self.db.execute_write_fn(write)

    async def list_shares(self, query_id: str) -> list[dict]:
        def read(conn):
            rows = conn.execute(
                """
                SELECT id, query_id, actor_id, can_edit, created_at
                FROM datasette_town_shares
                WHERE query_id = ?
                ORDER BY created_at
                """,
                [query_id],
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "query_id": r[1],
                    "actor_id": r[2],
                    "can_edit": bool(r[3]),
                    "created_at": r[4],
                }
                for r in rows
            ]

        return await self.db.execute_write_fn(read)

    async def get_share_for_actor(self, query_id: str, actor_id: str) -> dict | None:
        def read(conn):
            row = conn.execute(
                "SELECT id, query_id, actor_id, can_edit, created_at"
                " FROM datasette_town_shares WHERE query_id = ? AND actor_id = ?",
                [query_id, actor_id],
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "query_id": row[1],
                "actor_id": row[2],
                "can_edit": bool(row[3]),
                "created_at": row[4],
            }

        return await self.db.execute_write_fn(read)
