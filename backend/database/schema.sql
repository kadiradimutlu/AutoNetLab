DROP TABLE IF EXISTS validation_results;
DROP TABLE IF EXISTS injected_errors;
DROP TABLE IF EXISTS lab_sessions;
DROP TABLE IF EXISTS topologies;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE topologies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topology_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    description TEXT,
    yaml_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lab_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_code TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    topology_id INTEGER NOT NULL,
    difficulty TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    score INTEGER,
    progress INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (topology_id) REFERENCES topologies(id)
);

CREATE TABLE injected_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    device_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    description TEXT NOT NULL,
    expected_fix TEXT,
    is_fixed INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (session_id) REFERENCES lab_sessions(id)
);

CREATE TABLE validation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    related_topic TEXT,
    score_impact INTEGER NOT NULL DEFAULT 0,
    checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES lab_sessions(id)
);