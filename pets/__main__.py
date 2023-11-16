import asyncio
import rctogether

from . import Agency


async def main():
    async with rctogether.RestApiSession() as session:
        agency = await Agency.create(session)

        async for entity in rctogether.WebsocketSubscription():
            await agency.handle_entity(entity)


if __name__ == "__main__":
    asyncio.run(main())
