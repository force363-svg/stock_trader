"""
SQLite 테이블 정의
"""

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS stocks (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    market      TEXT,           -- KOSPI / KOSDAQ
    sector      TEXT,
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS daily_scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    code        TEXT NOT NULL,
    name        TEXT,
    total_score REAL,
    supply_score REAL,
    chart_score  REAL,
    material_score REAL,
    signal_type  TEXT,          -- BUY / HOLD / WATCH
    created_at   TEXT,
    UNIQUE(date, code)
);

CREATE TABLE IF NOT EXISTS signals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,
    code         TEXT NOT NULL,
    name         TEXT,
    signal_type  TEXT,          -- BUY / SELL / HOLD
    score        REAL,
    current_price INTEGER,
    stop_loss    INTEGER,
    target_price INTEGER,
    confidence   TEXT,          -- HIGH / MEDIUM / LOW
    conditions   TEXT,          -- JSON
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS trade_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT NOT NULL,
    name         TEXT,
    buy_date     TEXT,
    sell_date    TEXT,
    buy_price    INTEGER,
    sell_price   INTEGER,
    qty          INTEGER,
    pnl          REAL,          -- 손익률 %
    signal_score REAL,          -- 매수 당시 AI 점수
    conditions   TEXT,          -- JSON (매수 당시 조건별 점수)
    result       TEXT,          -- WIN / LOSS
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS weight_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    condition    TEXT NOT NULL,
    old_weight   REAL,
    new_weight   REAL,
    accuracy     REAL,          -- 해당 조건 적중률
    reason       TEXT,
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS condition_config (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name   TEXT NOT NULL,  -- screening / scoring / sell
    condition    TEXT NOT NULL,
    description  TEXT,
    weight       REAL DEFAULT 1.0,
    threshold    REAL,
    enabled      INTEGER DEFAULT 1,
    sort_order   INTEGER DEFAULT 0,
    updated_at   TEXT,
    UNIQUE(group_name, condition)
);
"""
