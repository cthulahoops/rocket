import asyncio
import json
import rctogether


async def main():
    async with rctogether.RestApiSession() as session:
        bots = await rctogether.bots.get(session)
        print(json.dumps(bots))


if __name__ == "__main__":
    asyncio.run(main())
