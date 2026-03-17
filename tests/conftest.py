import os
import pytest
import sqlite3

from datasette.app import Datasette

# Use dev mode for vite so we don't need a built manifest
os.environ["DATASETTE_TOWN_VITE_PATH"] = "http://localhost:5180/"


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE test_table (id integer primary key, name text)")
    conn.execute("INSERT INTO test_table VALUES (1, 'alice')")
    conn.execute("INSERT INTO test_table VALUES (2, 'bob')")
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def datasette_instance(db_path):
    return Datasette(
        [str(db_path)],
        config={
            "permissions": {
                "datasette-town-access": {"id": "*"},
                "datasette-town-create": {"id": "*"},
                "datasette-town-view-shared": {"id": "*"},
                "datasette-town-edit-shared": {"id": "*"},
            }
        },
    )
