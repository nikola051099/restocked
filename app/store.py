"""
Minimal persistence layer.

Uses Postgres if DATABASE_URL is set, otherwise an in-memory dict so the app
runs locally with zero setup. Stores per-shop access tokens, settings, and the
latest computed recommendations.
"""
from __future__ import annotations

import json
from .config import settings

_MEM: dict[str, dict] = {}


class Store:
    def __init__(self):
        self.use_db = bool(settings.DATABASE_URL)
        if self.use_db:
            from sqlalchemy import create_engine, text
            self._engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            self._text = text
            with self._engine.begin() as c:
                c.execute(text(
                    "CREATE TABLE IF NOT EXISTS shops ("
                    "shop TEXT PRIMARY KEY, data JSONB NOT NULL)"
                ))

    def get(self, shop: str) -> dict:
        if self.use_db:
            with self._engine.begin() as c:
                row = c.execute(self._text("SELECT data FROM shops WHERE shop=:s"),
                                {"s": shop}).fetchone()
                return dict(row[0]) if row else {}
        return dict(_MEM.get(shop, {}))

    def put(self, shop: str, data: dict) -> None:
        if self.use_db:
            with self._engine.begin() as c:
                c.execute(self._text(
                    "INSERT INTO shops (shop, data) VALUES (:s, :d) "
                    "ON CONFLICT (shop) DO UPDATE SET data = :d"
                ), {"s": shop, "d": json.dumps(data)})
        else:
            _MEM[shop] = data

    def update(self, shop: str, **fields) -> dict:
        data = self.get(shop)
        data.update(fields)
        self.put(shop, data)
        return data

    def delete(self, shop: str) -> None:
        if self.use_db:
            with self._engine.begin() as c:
                c.execute(self._text("DELETE FROM shops WHERE shop=:s"), {"s": shop})
        else:
            _MEM.pop(shop, None)

    def all_shops(self) -> list[str]:
        if self.use_db:
            with self._engine.begin() as c:
                rows = c.execute(self._text("SELECT shop FROM shops")).fetchall()
                return [r[0] for r in rows]
        return list(_MEM.keys())


store = Store()
