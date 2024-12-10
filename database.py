from pymongo import MongoClient
import os
from dotenv import main

main.load_dotenv()

cluster = MongoClient(f"{os.getenv('DB_URI')}")
db = cluster["based_count"]
collection = db["messages"]
kek_counter = db["kek_counter"]
gambling_list = db["gambling"]
stocks = db["stocks"]
stock_history = db["stock_history"]