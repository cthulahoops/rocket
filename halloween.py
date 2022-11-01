import asyncio
import rctogether
import random

COSTUMES = ["👻", "🦇", "🧟", "🎃"]

async def main():
    async with rctogether.RestApiSession() as session:
        bots = await rctogether.bots.get(session)
        for bot in bots:
            if bot['emoji'] in COSTUMES:
                continue
            print(bot)
            if bot['emoji'] == '🧞':
                continue
            costume = random.choice(COSTUMES)
            print(costume)
            await rctogether.bots.update(session, bot['id'], {'emoji': costume})
            await asyncio.sleep(0.2)

if __name__ == "__main__":
    asyncio.run(main())
