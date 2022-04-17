from pymongo import mongo_client
import env

client = mongo_client.MongoClient(env.DATABASE_CONNECTION_STRING)

guild_collection = client['Guilds'].get_collection('Guild')
command_collection = client['Guilds'].get_collection('CommandInfo')


def get_all_commands():
  return command_collection.find()

def get_command_info(command_name: str):
  return command_collection.find_one({'name': command_name})['description']

def get_all_guilds():
  return guild_collection.find()

def get_guild_json(guild_id: int):
  return guild_collection.find_one({'_id': guild_id})

def create_guild_json(data: dict):
  guild_collection.insert_one(data)

def write_guild_json(guild_id: int, data: dict):
  guild_collection.replace_one({'_id': guild_id}, data)