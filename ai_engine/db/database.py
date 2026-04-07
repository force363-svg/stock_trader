"""
SQLite 연결 및 초기화
DB 파일: C:\StockTrader\ai_engine.db (exe) 또는 stock_trader/ai_engine.db (개발)
"""
import sqlite3
import os
import sys
from .models import CREATE_TABLES


def get_db_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "ai_engine.db")


def get_connection():
    """DB 연결 반환 (없으면 생성)"""
    path = get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    """테이블 초기화"""
    conn = get_connection()
    try:
        conn.executescript(CREATE_TABLES)
        conn.commit()
        print(f"[DB] 초기화 완료: {get_db_path()}")
    finally:
        conn.close()
