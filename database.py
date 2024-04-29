from pymongo import MongoClient
import os
import dotenv

dotenv.load_dotenv()

cluster = MongoClient(f"{os.environ['DB_URI']}")
db = cluster["based_count"]
collection = db["messages"]
kek_counter = db["kek_counter"]
gambling_list = db["gambling"]