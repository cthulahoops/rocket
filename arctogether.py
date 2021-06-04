import os
import traceback
import json
import asyncio
import aiohttp
import websockets

RC_APP_ID = os.environ["RC_APP_ID"]
RC_APP_SECRET = os.environ["RC_APP_SECRET"]
RC_APP_ENDPOINT = os.environ.get("RC_ENDPOINT", "recurse.rctogether.com")


class HttpError(Exception):
    pass


def api_url(resource, resource_id=None):
    if resource_id is not None:
        resource = f"{resource}/{resource_id}"

    return f"https://{RC_APP_ENDPOINT}/api/{resource}?app_id={RC_APP_ID}&app_secret={RC_APP_SECRET}"


async def parse_response(response):
    if response.status != 200:
        body = await response.text()
        raise HttpError(response.status, body)
    return await response.json()


async def get_bots():
    async with aiohttp.ClientSession() as session:
        async with session.get(url=api_url("bots")) as response:
            return await parse_response(response)


async def delete_bot(bot_id):
    async with aiohttp.ClientSession() as session:
        async with session.delete(url=api_url("bots", bot_id)) as response:
            return await parse_response(response)


async def create_bot(name, emoji, x=5, y=2, direction="right", can_be_mentioned=False):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            api_url("bots"),
            json={
                "bot": {
                    "name": name,
                    "emoji": emoji,
                    "x": x,
                    "y": y,
                    "direction": direction,
                    "can_be_mentioned": can_be_mentioned,
                }
            },
        ) as response:
            return await parse_response(response)


async def update_bot(bot_id, bot_attributes):
    async with aiohttp.ClientSession() as session:
        async with session.patch(api_url("bots", bot_id), json={"bot": bot_attributes}) as response:
            return await parse_response(response)


async def send_message(bot_id, message_text):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=api_url("messages"), json={"bot_id": bot_id, "text": message_text}
        ) as response:
            return await parse_response(response)


async def clean_up_bots():
    bots = await get_bots()
    asyncio.gather(*[delete_bot(bot["id"]) for bot in bots])


def with_tracebacks(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise

    return wrapper


class Bot:
    def __init__(self, bot_json, handle_update=None):
        self.bot_json = bot_json
        self.queue = asyncio.Queue()
        self.handle_update = handle_update

    @classmethod
    async def create(cls, name, emoji, x, y, handle_update=None, can_be_mentioned=False):
        bot_json = await create_bot(
            name=name, emoji=emoji, x=x, y=y, can_be_mentioned=can_be_mentioned
        )
        bot = cls(bot_json, handle_update)
        asyncio.create_task(bot.run())
        return bot

    @property
    def id(self):
        return self.bot_json["id"]

    @property
    def emoji(self):
        return self.bot_json["emoji"]

    @property
    def name(self):
        return self.bot_json["name"]

    async def run(self):
        while True:
            update = await self.queue.get()
            while not self.queue.empty():
                print("Skipping outdated update: ", update)
                update = await self.queue.get()
            print("Applying update: ", update)
            try:
                await update_bot(self.id, update)
            except HttpError as exc:
                print(f"Update failed: {self!r}, {exc!r}")
            await asyncio.sleep(1)

    async def update(self, update):
        await self.queue.put(update)

    def update_data(self, data):
        self.bot_json = data

    async def handle_entity(self, entity):
        print("Bot update!")
        self.bot_json = entity
        if self.handle_update:
            await self.handle_update(entity)

    def __repr__(self):
        return "<Bot name=%r>" % (self.name,)


class RcTogether:
    def __init__(self, callbacks=()):
        self.callbacks = callbacks
        self.bots = {}

    async def run_websocket(self):
        origin = f"https://{RC_APP_ENDPOINT}"
        url = f"wss://{RC_APP_ENDPOINT}/cable?app_id={RC_APP_ID}&app_secret={RC_APP_SECRET}"

        async with websockets.connect(url, ssl=True, origin=origin) as connection:
            subscription_identifier = json.dumps({"channel": "ApiChannel"})
            async for msg in connection:
                data = json.loads(msg)

                message_type = data.get("type")

                if message_type == "ping":
                    pass
                elif message_type == "welcome":
                    await connection.send(
                        json.dumps({"command": "subscribe", "identifier": subscription_identifier})
                    )
                elif message_type == "confirm_subscription":
                    print("Subscription confirmed.")
                elif message_type == "reject_subscription":
                    raise ValueError("RcTogether: Subscription rejected.")
                elif (
                    "identifier" in data
                    and data["identifier"] == subscription_identifier
                    and "message" in data
                ):
                    await self.handle_message(data["message"])
                else:
                    print("Unknown message type: ", message_type)

    async def create_bot(self, name, emoji, x, y, handle_update, can_be_mentioned=False):
        bot = await Bot.create(name, emoji, x, y, handle_update, can_be_mentioned)
        self.bots[bot.id] = bot
        return bot

    async def handle_message(self, message):
        if message["type"] == "world":
            for entity in message["payload"]["entities"]:
                await self.handle_entity(entity)
        else:
            await self.handle_entity(message["payload"])

    async def handle_entity(self, entity):
        for callback in self.callbacks:
            await callback(entity)

        if entity["id"] in self.bots:
            callback = self.bots[entity["id"]].handle_entity
            if callback:
                await callback(entity)

    def add_callback(self, callback):
        self.callbacks.append(callback)
