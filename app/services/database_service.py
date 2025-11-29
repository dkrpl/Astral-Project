import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_config: Dict):
        """
        Bridge-first database service - always use bridge to avoid firewall issues
        """
        self.db_config = db_config or {}
        self.connection = None
        self._conn_params = self.db_config.get("connection_params") or {}
        
        # Bridge configuration - REQUIRED
        self._bridge_url = (
            self._conn_params.get("bridge_url") or 
            self.db_config.get("bridge_url")
        )
        
        self._bridge_key = (
            self._conn_params.get("bridge_api_key") or 
            self.db_config.get("bridge_key")
        )
        
        self._system_type = (self.db_config.get("system_type") or "mysql").lower()

    async def _call_bridge(self, action: str, payload: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
        """Call bridge API - this is the PRIMARY method"""
        if not self._bridge_url:
            return {"success": False, "message": "Bridge URL not configured"}

        url = self._bridge_url.rstrip("/") + f"?action={action}"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AstralAI/1.0"
        }
        
        if self._bridge_key:
            headers["X-API-Key"] = self._bridge_key

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Calling bridge: {url}")
                resp = await client.post(url, json=payload or {}, headers=headers)
                
                if resp.status_code != 200:
                    return {
                        "success": False, 
                        "message": f"Bridge returned status {resp.status_code}: {resp.text}"
                    }
                
                try:
                    result = resp.json()
                    logger.info(f"Bridge response: {result.get('success', False)}")
                    return result
                except Exception as e:
                    return {
                        "success": False, 
                        "message": f"Bridge returned invalid JSON: {resp.text}"
                    }
                    
        except httpx.ConnectError:
            return {"success": False, "message": "Cannot connect to bridge server"}
        except httpx.TimeoutException:
            return {"success": False, "message": "Bridge request timeout"}
        except Exception as e:
            logger.error(f"Bridge call error: {str(e)}")
            return {"success": False, "message": f"Bridge error: {str(e)}"}

    async def connect(self) -> bool:
        """Bridge-first - always return True since we use bridge"""
        return True

    async def disconnect(self):
        """No need to disconnect with bridge"""
        pass

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection via BRIDGE only
        """
        bridge_payload = {
            "system_type": self._system_type,
            "db_host": self.db_config.get("db_host"),
            "db_port": int(self.db_config.get("db_port", 3306)),
            "db_name": self.db_config.get("db_name"),
            "db_username": self.db_config.get("db_username"),
            "db_password": self.db_config.get("db_password"),
            "connection_params": self._conn_params
        }
        
        logger.info(f"Testing connection via bridge: {self._bridge_url}")
        result = await self._call_bridge("test", bridge_payload, timeout=20)
        result["method"] = "bridge"
        return result

    async def get_table_schema(self) -> Dict[str, Any]:
        """
        Get schema via BRIDGE only
        """
        bridge_payload = {
            "system_type": self._system_type,
            "db_host": self.db_config.get("db_host"),
            "db_port": int(self.db_config.get("db_port", 3306)),
            "db_name": self.db_config.get("db_name"),
            "db_username": self.db_config.get("db_username"),
            "db_password": self.db_config.get("db_password"),
            "connection_params": self._conn_params
        }
        
        logger.info(f"Getting schema via bridge: {self._bridge_url}")
        result = await self._call_bridge("schema", bridge_payload, timeout=60)
        result["method"] = "bridge"
        return result

    async def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute query via BRIDGE only
        """
        bridge_payload = {
            "system_type": self._system_type,
            "db_host": self.db_config.get("db_host"),
            "db_port": int(self.db_config.get("db_port", 3306)),
            "db_name": self.db_config.get("db_name"),
            "db_username": self.db_config.get("db_username"),
            "db_password": self.db_config.get("db_password"),
            "query": query,
            "connection_params": self._conn_params
        }
        
        logger.info(f"Executing query via bridge: {query[:100]}...")
        result = await self._call_bridge("execute", bridge_payload, timeout=60)
        result["method"] = "bridge"
        return result