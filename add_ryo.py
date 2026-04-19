import asyncio
import motor.motor_asyncio

MONGO_URI = "mongodb+srv://Multiverse_user:Multiverse123@multiverse.pgqfvsu.mongodb.net/?appName=Multiverse"
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["multiverse_bot"]

async def main():
    users = await db["users"].find({}).to_list(length=None)
    print(f"Found {len(users)} user(s) in database")

    if not users:
        print("No users found. Register first with /start in Telegram.")
        return

    for u in users:
        result = await db["users"].update_one(
            {"user_id": u["user_id"]},
            {"$inc": {"currencies.ryo": 1000}}
        )
        new = await db["users"].find_one({"user_id": u["user_id"]})
        new_ryo = new["currencies"]["ryo"]
        print(f"[OK] User: {u.get('username', '?')} (ID: {u['user_id']})")
        print(f"     +1000 Ryo added | New balance: {new_ryo} Ryo")

asyncio.run(main())
