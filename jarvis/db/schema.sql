-- Jarvis State DB Schema
-- Run: sqlite3 ~/jarvis/state.db < schema.sql

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- === TABLES ===

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','paused','done','archived')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    type TEXT NOT NULL,
    payload TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fitscan_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    value TEXT,
    status TEXT NOT NULL DEFAULT 'unknown' CHECK(status IN ('ok','warn','error','unknown')),
    checked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','in_progress','blocked','done')),
    priority INTEGER NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 5),
    due_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- === INDEXES ===

CREATE INDEX IF NOT EXISTS idx_events_project ON events(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fitscan_metric ON fitscan_state(metric, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, priority, due_at);

-- === VIEWS ===

CREATE VIEW IF NOT EXISTS v_fitscan_current AS
SELECT fs.*
FROM fitscan_state fs
INNER JOIN (
    SELECT metric, MAX(checked_at) AS max_checked
    FROM fitscan_state
    GROUP BY metric
) latest ON fs.metric = latest.metric AND fs.checked_at = latest.max_checked;

CREATE VIEW IF NOT EXISTS v_active_tasks AS
SELECT t.*, p.name AS project_name
FROM tasks t
LEFT JOIN projects p ON t.project_id = p.id
WHERE t.status != 'done'
ORDER BY t.priority ASC, t.due_at ASC NULLS LAST;

CREATE VIEW IF NOT EXISTS v_recent_events AS
SELECT e.*, p.name AS project_name
FROM events e
LEFT JOIN projects p ON e.project_id = p.id
ORDER BY e.created_at DESC
LIMIT 50;

CREATE VIEW IF NOT EXISTS v_project_summary AS
SELECT
    p.id,
    p.name,
    p.slug,
    p.status,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status != 'done') AS open_tasks,
    COUNT(DISTINCT e.id) AS total_events,
    MAX(e.created_at) AS last_event_at
FROM projects p
LEFT JOIN tasks t ON t.project_id = p.id
LEFT JOIN events e ON e.project_id = p.id
GROUP BY p.id;

CREATE VIEW IF NOT EXISTS v_daily_digest AS
SELECT
    p.name AS project_name,
    e.type,
    e.payload,
    e.created_at
FROM events e
LEFT JOIN projects p ON e.project_id = p.id
WHERE date(e.created_at) = date('now')
ORDER BY e.created_at DESC;

-- === SEED DATA ===

INSERT OR IGNORE INTO projects (name, slug, status) VALUES ('FitScan', 'fitscan', 'active');
INSERT OR IGNORE INTO config (key, value) VALUES
    ('telegram_chat_id', ''),
    ('n8n_base_url', 'http://localhost:5678'),
    ('fitscan_github_repo', ''),
    ('fitscan_deploy_url', ''),
    ('fitscan_shopify_store', ''),
    ('collector_interval_min', '15');
