import os
import sqlite3
from datetime import datetime
from pathlib import Path

from core.crypto import KeyManager


class DatabaseManager:
    def __init__(self, data_dir: Path, master_password: str):
        self.db_path = data_dir / "wifi.db"
        self._master_password = master_password
        self._crypto: KeyManager | None = None
        data_dir.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA secure_delete = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

        self._init_db()
        self._salt = self._get_salt()

    @property
    def crypto(self) -> KeyManager:
        if self._crypto is None:
            self._crypto = KeyManager(self._master_password, self._salt)
        return self._crypto

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY,
                ssid TEXT UNIQUE NOT NULL,
                password_encrypted BLOB,
                security TEXT DEFAULT 'psk',
                auto_connect INTEGER DEFAULT 0,
                last_connected TEXT
            );
            CREATE TABLE IF NOT EXISTS key_meta (
                id INTEGER PRIMARY KEY,
                salt BLOB NOT NULL,
                key_version INTEGER DEFAULT 1
            );
        """)
        self.conn.commit()

    def _get_salt(self) -> bytes:
        row = self.conn.execute("SELECT salt FROM key_meta LIMIT 1").fetchone()
        if row:
            return row[0]
        salt = os.urandom(16)
        self.conn.execute("INSERT INTO key_meta (salt) VALUES (?)", (salt,))
        self.conn.commit()
        return salt

    def save_network(self, ssid: str, password: str | None, security: str = "psk"):
        encrypted = self.crypto.encrypt(password) if password else None
        self.conn.execute(
            """INSERT OR REPLACE INTO networks
               (ssid, password_encrypted, security, last_connected)
               VALUES (?, ?, ?, ?)""",
            (ssid, encrypted, security, datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_password(self, ssid: str) -> str | None:
        row = self.conn.execute(
            "SELECT password_encrypted FROM networks WHERE ssid = ?", (ssid,)
        ).fetchone()
        if row and row[0]:
            return self.crypto.decrypt(row[0])
        return None

    def get_network(self, ssid: str) -> dict | None:
        row = self.conn.execute(
            "SELECT ssid, security, auto_connect, last_connected FROM networks WHERE ssid = ?",
            (ssid,),
        ).fetchone()
        if row:
            return {
                "ssid": row[0],
                "security": row[1],
                "auto_connect": bool(row[2]),
                "last_connected": row[3],
            }
        return None

    def list_networks(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT ssid, security, auto_connect, last_connected FROM networks ORDER BY last_connected DESC"
        ).fetchall()
        return [
            {
                "ssid": r[0],
                "security": r[1],
                "auto_connect": bool(r[2]),
                "last_connected": r[3],
            }
            for r in rows
        ]

    def delete_network(self, ssid: str):
        self.conn.execute("DELETE FROM networks WHERE ssid = ?", (ssid,))
        self.conn.commit()

    def set_auto_connect(self, ssid: str, value: bool):
        self.conn.execute(
            "UPDATE networks SET auto_connect = ? WHERE ssid = ?", (int(value), ssid)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
