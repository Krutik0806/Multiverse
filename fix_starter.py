"""
One-time fix: give existing user (krutik_08_06) their starter character
and set them as team[0].
"""
import asyncio
import motor.motor_asyncio
from datetime import datetime, timezone

MONGO_URI = "mongodb+srv://Multiverse_user:Multiverse123@multiverse.pgqfvsu.mongodb.net/?appName=Multiverse"
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["multiverse_bot"]

STARTER = {"naruto": "iruka", "aot": "marco"}

async def main():
    users = await db["users"].find({}).to_list(length=None)
    print(f"Found {len(users)} user(s)")

    for u in users:
        world = u["world"]
        starter_id = STARTER[world]
        uid = u["user_id"]

        # Check if starter already in characters collection
        existing = await db["characters"].find_one({"owner_id": uid, "char_id": starter_id})
        if not existing:
            await db["characters"].insert_one({
                "owner_id": uid,
                "char_id": starter_id,
                "stars": 1,
                "duplicates": 0,
                "obtained_at": datetime.now(timezone.utc),
            })
            print(f"  [OK] Added starter char '{starter_id}' to user {u['username']}")
        else:
            print(f"  [SKIP] User {u['username']} already has '{starter_id}'")

        # Set team if empty
        if not u.get("team"):
            await db["users"].update_one(
                {"user_id": uid},
                {"$set": {"team": [starter_id]}}
            )
            print(f"  [OK] Set team to [{starter_id}]")
        else:
            print(f"  [SKIP] User {u['username']} already has a team: {u['team']}")

asyncio.run(main())
