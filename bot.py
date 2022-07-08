import asyncio
import rctogether

class Bot:
    def __init__(self, bot_json):
        self.bot_json = bot_json
        self.queue = asyncio.Queue()
        self.task = None

    @classmethod
    async def create(cls, session, name, emoji, x, y, can_be_mentioned=False):
        bot_json = await rctogether.bots.create(
            session, name=name, emoji=emoji, x=x, y=y, can_be_mentioned=can_be_mentioned
        )
        bot = cls(bot_json)
        bot.start_task(session)
        return bot

    async def close(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass


    def start_task(self, session):
        self.task = asyncio.create_task(self.run(session))

    @property
    def pos(self):
        return self.bot_json["pos"]

    @property
    def id(self):
        return self.bot_json["id"]

    @property
    def emoji(self):
        return self.bot_json["emoji"]

    @property
    def name(self):
        return self.bot_json["name"]

    async def get_queued_update(self):
        update = await self.queue.get()

        while update is not None and not self.queue.empty():
            print("Skipping outdated update: ", update)
            update = await self.queue.get()

        return update

    async def run(self, session):
        while True:
            update = await self.get_queued_update()
            print("Applying update: ", update)
            try:
                await rctogether.bots.update(session, self.id, update)
            except rctogether.api.HttpError as exc:
                print(f"Update failed: {self!r}, {exc!r}")
            await asyncio.sleep(1)

    async def update(self, update):
        await self.queue.put(update)

    async def destroy(self, session):
        rctogether.bots.delete(session, self.id)

    def update_data(self, data):
        self.bot_json = data
