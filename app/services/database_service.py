import logging
from typing import Dict, Any, Optional

import pymysql
import psycopg2
import psycopg2.extras
import httpx

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_config: Dict):
        """
        db_config expected keys (kept compatible with strukturmu):
          - db_host, db_port, db_name, db_username, db_password
          - system_type (optional) e.g. "mysql" or "postgres"
          - connection_params (optional dict) -> may contain 'bridge_url' and 'bridge_api_key'
        """
        self.db_config = db_config or {}
        self.connection = None
        self._conn_params = self.db_config.get("connection_params") or {}
        self._bridge_url = self._conn_params.get("bridge_url") or self.db_config.get("bridge_url")
        self._bridge_key = self._conn_params.get("bridge_api_key") or self.db_config.get("bridge_key")
        self._system_type = (self.db_config.get("system_type") or "mysql").lower()

    # -------------------------
    # Bridge helpers
    # -------------------------
    async def _call_bridge(self, action: str, payload: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
        if not self._bridge_url:
            return {"success": False, "message": "Bridge URL not provided"}

        url = self._bridge_url
        if "?" in url:
            # if user already provided query param, keep it; else we'll append
            pass
        # Bridge expects ?action=...
        url_with_action = url.rstrip("/") + f"?action={action}"

        headers = {}
        if self._bridge_key:
            headers["X-API-Key"] = self._bridge_key

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url_with_action, json=payload or {}, headers=headers)
                # try parse json
                try:
                    return resp.json()
                except Exception:
                    return {"success": False, "message": f"Bridge returned non-json: {resp.text}"}
        except Exception as e:
            logger.exception("Error contacting bridge")
            return {"success": False, "message": str(e)}

    # -------------------------
    # Direct connection helpers
    # -------------------------
    def _direct_mysql_connect(self):
        return pymysql.connect(
            host=self.db_config['db_host'],
            port=int(self.db_config.get('db_port', 3306)),
            user=self.db_config['db_username'],
            password=self.db_config['db_password'],
            database=self.db_config.get('db_name'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            **(self._conn_params.get('driver_options', {}) if isinstance(self._conn_params.get('driver_options', {}), dict) else {})
        )

    def _direct_postgres_connect(self):
        # psycopg2 accepts keyword args
        kwargs = {
            "host": self.db_config['db_host'],
            "port": int(self.db_config.get('db_port', 5432)),
            "user": self.db_config['db_username'],
            "password": self.db_config['db_password'],
            "dbname": self.db_config.get('db_name'),
        }
        # merge additional params if provided
        driver_opts = self._conn_params.get('driver_options') or {}
        kwargs.update(driver_opts)
        return psycopg2.connect(cursor_factory=psycopg2.extras.RealDictCursor, **kwargs)

    # -------------------------
    # Public API (same names as before)
    # -------------------------
    async def connect(self) -> bool:
        """Try to create a direct connection (MySQL/Postgres). Return True if success."""
        try:
            if self._system_type in ("mysql", "mariadb"):
                self.connection = self._direct_mysql_connect()
                logger.info("Connected directly via MySQL")
                return True

            if self._system_type in ("postgres", "postgresql"):
                self.connection = self._direct_postgres_connect()
                logger.info("Connected directly via Postgres")
                return True

            # Unsupported direct type -> treat as failure to trigger bridge fallback
            logger.warning(f"Unsupported direct system_type: {self._system_type}")
            return False

        except Exception as e:
            logger.warning(f"Direct connection failed: {e}")
            # do NOT raise — we want fallback to bridge
            return False

    async def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

    async def test_connection(self) -> Dict[str, Any]:
        """
        Try direct connection → if ok return success.
        If direct fails, automatically call bridge/test.
        """
        # Try direct
        direct_ok = await self.connect()
        if direct_ok:
            try:
                # run a small test to confirm DB works
                if self._system_type in ("mysql", "mariadb"):
                    with self.connection.cursor() as cur:
                        cur.execute("SELECT 1 as connection_test")
                        row = cur.fetchone()
                    return {"success": True, "message": "Direct MySQL connection successful", "data": row, "method": "direct"}
                else:
                    with self.connection.cursor() as cur:
                        cur.execute("SELECT 1 as connection_test")
                        row = cur.fetchone()
                    return {"success": True, "message": "Direct Postgres connection successful", "data": row, "method": "direct"}
            except Exception as e:
                logger.warning(f"Direct test query failed: {e}")
                # fallthrough to bridge
        # Fallback: call bridge
        bridge_payload = {
            "system_type": self._system_type,
            "db_host": self.db_config.get("db_host"),
            "db_port": int(self.db_config.get("db_port")) if self.db_config.get("db_port") else None,
            "db_name": self.db_config.get("db_name"),
            "db_username": self.db_config.get("db_username"),
            "db_password": self.db_config.get("db_password"),
            "connection_params": self._conn_params
        }
        return await self._call_bridge("test", bridge_payload, timeout=20)

    async def get_table_schema(self) -> Dict[str, Any]:
        """
        Try direct schema retrieval; fallback to bridge if direct fails.
        Returns either dict schema or bridge response.
        """
        # Try direct
        direct_ok = await self.connect()
        if direct_ok:
            try:
                schema = {}
                if self._system_type in ("mysql", "mariadb"):
                    with self.connection.cursor() as cur:
                        cur.execute("SHOW TABLES")
                        tables = cur.fetchall()
                        for t in tables:
                            # pymysql DictCursor yields { 'Tables_in_dbname': 'table' } key differs
                            table_name = list(t.values())[0]
                            cur.execute(f"DESCRIBE `{table_name}`")
                            columns = cur.fetchall()
                            schema[table_name] = {
                                "columns": [c['Field'] for c in columns],
                                "column_details": columns
                            }
                else:  # postgres
                    with self.connection.cursor() as cur:
                        cur.execute("""
                            SELECT table_name FROM information_schema.tables
                            WHERE table_schema = 'public' AND table_type='BASE TABLE'
                        """)
                        tables = cur.fetchall()
                        for t in tables:
                            table_name = t['table_name']
                            cur.execute("""
                                SELECT column_name, data_type, is_nullable
                                FROM information_schema.columns
                                WHERE table_name = %s
                            """, (table_name,))
                            cols = cur.fetchall()
                            schema[table_name] = {
                                "columns": [c['column_name'] for c in cols],
                                "column_details": cols
                            }
                return {"success": True, "schema": schema, "table_count": len(schema), "method": "direct"}
            except Exception as e:
                logger.warning(f"Direct get_table_schema failed: {e}")
                # fall through to bridge
        # Fallback: bridge
        bridge_payload = {
            "system_type": self._system_type,
            "db_host": self.db_config.get("db_host"),
            "db_port": int(self.db_config.get("db_port")) if self.db_config.get("db_port") else None,
            "db_name": self.db_config.get("db_name"),
            "db_username": self.db_config.get("db_username"),
            "db_password": self.db_config.get("db_password"),
            "connection_params": self._conn_params
        }
        return await self._call_bridge("schema", bridge_payload, timeout=60)

    async def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Try direct execution; fallback to bridge if direct fails.
        NOTE: For safety the bridge only accepts SELECT (bridge side restriction).
        """
        # Try direct
        direct_ok = await self.connect()
        if direct_ok:
            try:
                if self._system_type in ("mysql", "mariadb"):
                    with self.connection.cursor() as cur:
                        cur.execute(query)
                        if query.strip().upper().startswith("SELECT"):
                            rows = cur.fetchall()
                            return {"success": True, "data": rows, "row_count": len(rows), "method": "direct"}
                        else:
                            self.connection.commit()
                            return {"success": True, "affected_rows": cur.rowcount, "method": "direct"}
                else:  # postgres
                    with self.connection.cursor() as cur:
                        cur.execute(query)
                        if query.strip().upper().startswith("SELECT"):
                            rows = cur.fetchall()
                            return {"success": True, "data": rows, "row_count": len(rows), "method": "direct"}
                        else:
                            self.connection.commit()
                            return {"success": True, "affected_rows": cur.rowcount, "method": "direct"}
            except Exception as e:
                logger.warning(f"Direct execute_query failed: {e}")
                # fall through to bridge

        # Fallback: bridge
        bridge_payload = {
            "system_type": self._system_type,
            "db_host": self.db_config.get("db_host"),
            "db_port": int(self.db_config.get("db_port")) if self.db_config.get("db_port") else None,
            "db_name": self.db_config.get("db_name"),
            "db_username": self.db_config.get("db_username"),
            "db_password": self.db_config.get("db_password"),
            "query": query,
            "connection_params": self._conn_params
        }
        return await self._call_bridge("execute", bridge_payload, timeout=60)
