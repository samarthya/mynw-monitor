CREATE TABLE IF NOT EXISTS connection_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    pid INTEGER NOT NULL,
    process_name TEXT NOT NULL,
    local_addr TEXT NOT NULL,
    remote_addr TEXT NOT NULL,
    remote_port INTEGER NOT NULL,
    bytes_sent INTEGER NOT NULL DEFAULT 0,
    bytes_recv INTEGER NOT NULL DEFAULT 0,
    hostname TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'unknown'
);

CREATE INDEX IF NOT EXISTS idx_connection_events_timestamp ON connection_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_connection_events_hostname ON connection_events(hostname);
CREATE INDEX IF NOT EXISTS idx_connection_events_category ON connection_events(category);

CREATE TABLE IF NOT EXISTS domain_classifications (
    hostname TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
