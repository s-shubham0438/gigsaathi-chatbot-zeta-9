from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.mongo_db_uri)
print(client.admin.command("ping"))
client.close()