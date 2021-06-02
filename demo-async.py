import os
import random
import asyncio
import aiohttp

RC_APP_ID = os.environ["RC_APP_ID"]
RC_APP_SECRET = os.environ["RC_APP_SECRET"]
RC_APP_ENDPOINT = os.environ.get("RC_ENDPOINT", "recurse.rctogether.com")

def api_url(resource, resource_id=None):
    if resource_id is not None:
        resource = f"{resource}/{resource_id}"

    return f"https://{RC_APP_ENDPOINT}/api/{resource}?app_id={RC_APP_ID}&app_secret={RC_APP_SECRET}"

async def create_snake():
    x = random.randint(142, 175)
    y = random.randint(1, 40)

    print("Creating at: ", x, y)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            api_url("bots"),
            json={
                "bot": {
                    "name": "Assssssycio!!!",
                    "emoji": "🐍",
                    "x": x,
                    "y": y,
                    "direction": "right",
                    "can_be_mentioned": False,
                }}) as response:

            body = await response.text()
            print(body)

async def main():
    snakes = [create_snake() for _ in range(10)]
    print(snakes)
    await asyncio.gather(*snakes)

if __name__ == '__main__':
    asyncio.run(main())
