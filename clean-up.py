import asyncio
import rctogether

async def main():
    async with rctogether.RestApiSession() as session:
        # Refuse to clean up pets.
        if session.rc_app_id.startswith("c37fb"):
            raise ValueError("No! People care about pets")

        for bot in await rctogether.bots.get(session):
            await rctogether.bots.delete(session, bot['id'])

if __name__ == '__main__':
    asyncio.run(main())
