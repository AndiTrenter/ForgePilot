"""
Database Abstraction Layer
Zentrale Datenbank-Verwaltung mit Connection-Pooling
"""
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
import logging

from .config import get_config

logger = logging.getLogger(__name__)


class Database:
    """Datenbank-Singleton mit Connection-Management"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._connected = False
    
    async def connect(self):
        """Stellt Verbindung zur Datenbank her"""
        if self._connected:
            return
        
        config = get_config()
        
        try:
            self.client = AsyncIOMotorClient(
                config.database.url,
                maxPoolSize=config.database.max_pool_size,
                minPoolSize=config.database.min_pool_size
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            self.db = self.client[config.database.name]
            self._connected = True
            
            logger.info(f"✅ Verbunden mit MongoDB: {config.database.name}")
            
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB Connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Schließt Datenbankverbindung"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("🔌 MongoDB Verbindung geschlossen")
    
    def get_collection(self, name: str):
        """Gibt Collection zurück"""
        if not self._connected or not self.db:
            raise ConnectionFailure("Database not connected")
        return self.db[name]
    
    @property
    def projects(self):
        return self.get_collection("projects")
    
    @property
    def messages(self):
        return self.get_collection("messages")
    
    @property
    def agent_status(self):
        return self.get_collection("agent_status")
    
    @property
    def roadmap(self):
        return self.get_collection("roadmap")
    
    @property
    def logs(self):
        return self.get_collection("logs")
    
    @property
    def settings(self):
        return self.get_collection("settings")
    
    @property
    def update(self):
        return self.get_collection("update")
    
    @property
    def evidence(self):
        return self.get_collection("evidence")
    
    @property
    def tasks(self):
        return self.get_collection("tasks")


# Singleton Instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Gibt die globale Database-Instanz zurück"""
    global _db
    if _db is None:
        _db = Database()
    return _db


async def connect_database():
    """Stellt Datenbankverbindung her"""
    db = get_database()
    await db.connect()


async def disconnect_database():
    """Schließt Datenbankverbindung"""
    db = get_database()
    await db.disconnect()
