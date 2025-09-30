import logging
import random
import asyncio

import rctogether

# Currently we reimplement our own Bot class here.
# from bot import Bot

logging.basicConfig(level=logging.INFO)

# Launch station. (Where the rocket starts.)
# Control computer. (Note block check for name.)
# Collision detection.

CONTROL_COMPUTER = {"x": 27, "y": 61}
LAUNCH_PAD = {"x": 25, "y": 60}

TARGETS = {}
ROCKET_LOCATION = None


def normalise_name(name):
    if name is None:
        return None
    return name.strip("\n\r\t \u200b")


def first_name(s):
    return s.split(" ")[0]


def debris_message(emoji, target, instigator):
    return PAYLOADS[emoji] % {
        "victim": first_name(target),
        "instigator": first_name(instigator),
    }


PAYLOADS = {
    "💥": "%(victim)s was exploded by %(instigator)s",
    "🎉": "%(victim)s was aggressively thanked by %(instigator)s",
    "🐄": "COW!!!!!",
    "🔥": "%(victim)s is on fire",
    "💧": "WATER FIGHT!",
    "🌈": "%(victim)s got their groove back!",
    "💕": "%(victim)s was valentined by a secret admirer",
    "🍅": "%(victim)s was booed off stage by %(instigator)s",
    "🥉": "%(victim)s was THIRD PLACED by %(instigator)s",
    "☎️": "Hello. We’ve been trying to reach you with a message regarding your car’s extended warranty...",
    "💍": "%(instigator)s has proposed to %(victim)s at a sporting event.",
    "🍀": "%(instigator)s has sent good luck to %(victim)s.",
    "🌵": "%(instigator)s gave %(victim)s a nice gift! But can they keep it alive?",
    "🏉": "OUCH. %(instigator)s just threw a ball at %(victim)s's head.",
    "🦌": "%(victim)s was mowed down by an errant deer.",
    "🧸": "Sometimes %(victim)s just needs a cozy hug.",
    "🐣": "%(instigator)s has bequeathed %(victim)s with newfound responsibilites!",
}


class Bot:
    def __init__(self, bot_json):
        self.bot_json = bot_json
        self.queue = asyncio.Queue()
        self.task = None

    @classmethod
    async def create(cls, session, name, emoji, x, y):
        bot_json = await rctogether.bots.create(
            session, name=name, emoji=emoji, x=x, y=y
        )
        bot = cls(bot_json)
        bot.task = asyncio.create_task(bot.run(session))
        return bot

    @property
    def pos(self):
        return self.bot_json["pos"]

    @property
    def id(self):
        return self.bot_json["id"]

    async def run(self, session):
        while True:
            update = await self.queue.get()

            while update is not None and not self.queue.empty():
                print("Skipping outdated update: ", update)
                update = await self.queue.get()

            print("Applying update: ", update)
            await rctogether.bots.update(session, self.id, update)
            await asyncio.sleep(1)

    async def update(self, update):
        await self.queue.put(update)

    async def destroy(self, session):
        await rctogether.bots.delete(session, self.id)

    def update_data(self, data):
        self.bot_json = data


class ClankyBotLaunchSystem:
    def __init__(self, session, rocket, gc_bot):
        self.instigator = None
        self.target = "Nobody"
        self.session = session
        self.rocket = rocket
        self.gc_bot = gc_bot

    @classmethod
    async def create(cls, session):
        rocket = await Bot.create(
            session, name="Rocket Bot", emoji="🚀", x=LAUNCH_PAD["x"], y=LAUNCH_PAD["y"]
        )
        gc_bot = await GarbageCollectionBot.create(session)

        print("Rocket is : ", rocket)
        return cls(session, rocket, gc_bot)

    async def respawn_rocket(self):
        self.instigator = None
        self.rocket = await Bot.create(
            self.session,
            name="Rocket Bot",
            emoji="🚀",
            x=LAUNCH_PAD["x"],
            y=LAUNCH_PAD["y"],
        )
        self.target = "Nobody"

    async def handle_instruction(self, entity):
        print("New instructions received: ", entity)
        note_text = entity.get("note_text")
        if note_text == "":
            self.instigator = None
            self.target = "Nobody"
            await self.rocket.update(LAUNCH_PAD)
        else:
            self.instigator = entity.get("updated_by").get("name")
            self.target = normalise_name(note_text)
            if self.target in TARGETS:
                await self.rocket.update(TARGETS[self.target])

    async def handle_rocket_move(self, entity):
        self.rocket.update_data(entity)
        rocket_position = entity["pos"]
        target_position = TARGETS.get(self.target)

        print("TARGET HIT: ", rocket_position, target_position)
        if rocket_position == target_position:
            emoji = random.choice(list(PAYLOADS))
            await self.rocket.update(
                {
                    "emoji": emoji,
                    "name": debris_message(emoji, self.target, self.instigator),
                }
            )
            await self.gc_bot.add_garbage(self.rocket)
            await self.respawn_rocket()

    async def handle_target_detected(self, entity):
        target_position = entity["pos"]
        print("Target detected at: ", target_position)
        await self.rocket.update(target_position)

    async def handle_entity(self, entity):
        person_name = normalise_name(entity.get("person_name"))
        if person_name:
            TARGETS[person_name] = entity["pos"]

        if person_name == self.target:
            await self.handle_target_detected(entity)

        elif entity.get("pos") == CONTROL_COMPUTER:
            await self.handle_instruction(entity)

        elif entity["id"] == self.rocket.id:
            await self.handle_rocket_move(entity)

        elif entity["id"] == self.gc_bot.id:
            self.gc_bot.handle_update(entity)


GARBAGE_COLLECTION_HOME = {"x": 22, "y": 61}
MIN_GARBAGE_TO_COLLECT = 3


class GarbageCollectionBot:
    def __init__(self, session, garbage_bot):
        self.session = session
        self.garbage_bot = garbage_bot
        self.garbage_queue = asyncio.Queue()
        self.garbage = None

    @classmethod
    async def create(cls, session):
        garbage_bot = await Bot.create(
            session,
            name="Garbage Collector",
            emoji="🛺",
            **GARBAGE_COLLECTION_HOME,
        )
        gc_bot = cls(session, garbage_bot)
        asyncio.create_task(gc_bot.run(session))
        return gc_bot

    async def run(self, session):
        while True:
            if self.garbage_queue.qsize() <= MIN_GARBAGE_TO_COLLECT:
                await asyncio.sleep(60)
            elif self.garbage:
                print("Hey, we're already busy here.")
                await asyncio.sleep(60)
            else:
                await self.collect(await self.garbage_queue.get())

    @property
    def id(self):
        return self.garbage_bot.id

    async def add_garbage(self, garbage):
        await self.garbage_queue.put(garbage)

    async def collect(self, garbage):
        self.garbage = garbage
        print("Crew dispatched to collect: ", self.garbage)
        await self.garbage_bot.update(self.garbage.pos)

    async def complete_collection(self):
        await asyncio.sleep(15)
        print("Ready to complete collection!")
        await self.garbage.destroy(self.session)
        self.garbage = None
        await self.garbage_bot.update(GARBAGE_COLLECTION_HOME)

    def handle_update(self, entity):
        if self.garbage and entity["pos"] == self.garbage.pos:
            print("Collection complete: ", entity, self.garbage)
            asyncio.create_task(self.complete_collection())


async def main():
    async with rctogether.RestApiSession() as session:
        try:
            await rctogether.bots.delete_all(session)

            launch_system = await ClankyBotLaunchSystem.create(session)
            async for entity in rctogether.WebsocketSubscription():
                await launch_system.handle_entity(entity)
        finally:
            print("Exitting... cleaning up.")
            await rctogether.bots.delete_all(session)


if __name__ == "__main__":
    asyncio.run(main())
