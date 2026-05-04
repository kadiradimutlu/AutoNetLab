import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "autonetlab.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def initialize_database():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    connection = sqlite3.connect(DB_PATH)

    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
            schema_sql = schema_file.read()

        connection.executescript(schema_sql)
        seed_demo_data(connection)
        connection.commit()

        print("AutoNetLab SQLite database created successfully.")
        print(f"Database path: {DB_PATH}")

    finally:
        connection.close()


def seed_demo_data(connection):
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO users (username, full_name, role)
        VALUES (?, ?, ?)
        """,
        ("muhammed", "Muhammed YILDIZ", "student")
    )

    cursor.execute(
        """
        INSERT INTO topologies (
            topology_code,
            name,
            difficulty,
            description,
            yaml_path
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "topo-basic-01",
            "Two Switch VLAN Topology",
            "Easy",
            "A simple VLAN troubleshooting topology with two switches and two hosts.",
            "containerlab/topologies/sprint1-basic.clab.yml"
        )
    )

    user_id = cursor.lastrowid - 1
    topology_id = cursor.lastrowid

    cursor.execute(
        """
        SELECT id FROM users WHERE username = ?
        """,
        ("muhammed",)
    )
    user_id = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT id FROM topologies WHERE topology_code = ?
        """,
        ("topo-basic-01",)
    )
    topology_id = cursor.fetchone()[0]

    cursor.execute(
        """
        INSERT INTO lab_sessions (
            session_code,
            user_id,
            topology_id,
            difficulty,
            status,
            score,
            progress
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "sess-001",
            user_id,
            topology_id,
            "Easy",
            "in_progress",
            None,
            45
        )
    )

    cursor.execute(
        """
        SELECT id FROM lab_sessions WHERE session_code = ?
        """,
        ("sess-001",)
    )
    session_id = cursor.fetchone()[0]

    injected_errors = [
        (
            session_id,
            "Switch-1",
            "VLAN_MISCONFIGURATION",
            "VLAN 10 is missing on the access port.",
            "Create VLAN 10 and assign the correct access port.",
            1
        ),
        (
            session_id,
            "Switch-2",
            "TRUNK_MISCONFIGURATION",
            "The trunk link does not allow VLAN 10.",
            "Allow VLAN 10 on the trunk link between switches.",
            0
        )
    ]

    cursor.executemany(
        """
        INSERT INTO injected_errors (
            session_id,
            device_name,
            error_type,
            description,
            expected_fix,
            is_fixed
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        injected_errors
    )

    validation_results = [
        (
            session_id,
            "VLAN 10 exists on Switch-1",
            "PASS",
            "VLAN 10 is configured correctly on Switch-1.",
            "VLAN",
            25
        ),
        (
            session_id,
            "Trunk link allows VLAN 10",
            "FAIL",
            "The trunk link between Switch-1 and Switch-2 does not allow VLAN 10.",
            "Trunk Configuration",
            -25
        ),
        (
            session_id,
            "End-to-end connectivity",
            "FAIL",
            "PC1 cannot reach PC2. Check VLAN and trunk settings.",
            "Connectivity",
            -10
        )
    ]

    cursor.executemany(
        """
        INSERT INTO validation_results (
            session_id,
            check_name,
            status,
            message,
            related_topic,
            score_impact
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        validation_results
    )


if __name__ == "__main__":
    initialize_database()