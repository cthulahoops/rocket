import os
import random
import re
import datetime
from collections import defaultdict
import logging
import asyncio

import rctogether
from bot import Bot

logging.basicConfig(level=logging.INFO)

def parse_position(position):
    x, y = position.split(',')
    return {'x': int(x), 'y': int(y)}

def offset_position(position, delta):
    return {"x": position["x"] + delta["x"], "y": position["y"] + delta["y"]}

def is_adjacent(p1, p2):
    return abs(p2['x'] - p1['x']) <= 1 and abs(p2['y'] - p1['y']) <= 1

PETS = [
    {"emoji": "🦇", "name": "bat", "noise": "screech!"},
    {"emoji": "🐝", "name": "bee", "noise": "buzz!"},
    {"emoji": "🦕", "name": "brontosaurus", "noise": "MEEEHHH!"},
    {"emoji": "🐫", "name": "camel"},
    {"emoji": "🐈", "name": "cat", "noise": "miaow!"},
    {"emoji": "🐛", "name": "caterpillar", "noise": "munch!"},
    {"emoji": "🐄", "name": "cow", "noise": "Moo!"},
    {"emoji": "🦀", "name": "crab", "noise": "click!"},
    {"emoji": "🐊", "name": "crocodile"},
    {"emoji": "🐕", "name": "dog", "noise": "woof!"},
    {"emoji": "🐉", "name": "dragon", "noise": "🔥"},
    {"emoji": "🦅", "name": "eagle"},
    {"emoji": "🐘", "name": "elephant"},
    {"emoji": "🦩", "name": "flamingo"},
    {"emoji": "🦊", "name": "fox", "noise": "Wrahh!"},
    {"emoji": "🐸", "name": "frog", "noise": "ribbet!"},
    {"emoji": "🦒", "name": "giraffe"},
    {"emoji": "🦔", "name": "hedgehog", "noise": "scurry, scurry, scurry"},
    {"emoji": "🦛", "name": "hippo"},
    {"emoji": "👾", "name": "invader"},
    {"emoji": "🦘", "name": "kangaroo", "noise": "Chortle chortle!"},
    {"emoji": "🐨", "name": "koala", "noise": "gggrrrooowwwlll"},
    {"emoji": "🦙", "name": "llama"},
    {"emoji": "🐁", "name": "mouse", "noise": "squeak!"},
    {"emoji": "🦉", "name": "owl", "noise": "hoot hoot!"},
    {"emoji": "🦜", "name": "parrot", "noise": "HELLO!"},
    {"emoji": "🐧", "name": "penguin"},
    {"emoji": "🐖", "name": "pig", "noise": "oink!"},
    {"emoji": "🐇", "name": "rabbit"},
    {"emoji": "🚀", "name": "rocket"},
    {"emoji": "🐌", "name": "snail", "noise": "slurp!"},
    {"emoji": "🦖", "name": "t-rex", "noise": "RAWR!"},
    {"emoji": "🐅", "name": "tiger"},
    {"emoji": "🐢", "name": "turtle", "noise": "hiss!"},
    {"emoji": "🦄", "name": "unicorn", "noise": "✨"},
]

NOISES = {pet["emoji"]: pet.get("noise", "💖") for pet in PETS}

GENIE_NAME = os.environ.get('GENIE_NAME', 'Pet Agency Genie')
GENIE_HOME = parse_position(os.environ.get('GENIE_HOME', "60,15"))
SPAWN_POINTS = [
    offset_position(GENIE_HOME, {"x": dx, "y": dy})
    for (dx, dy) in [(-2, -2), (0, -2), (2, -2), (-2, 0), (2, 0), (0, 2), (2, 2)]
]

CORRAL = {"x": (0, 19), "y": (40, 58)}
PET_BOREDOM_TIMES = (3600, 5400)

SAD_MESSAGES = [
    "Was I not a good %(pet_name)s?",
    "I thought you liked me.",
    "😢",
    "What will I do now?",
    "But where will I go?",
    "One day I might learn to trust again...",
    "I only wanted to make you happy.",
    "My heart hurts.",
    "Did I do something wrong?",
    "But why?",
    "💔",
]

MANNERS = [
    "please",
    "bitte",
    "le do thoil",
    "sudo",
    "per favore",
    "oh mighty djinn",
    "s'il vous plaît",
    "s'il vous plait",
    "svp",
    "por favor",
    "kudasai",
    "onegai shimasu",
    "пожалуйста",
]

THANKS_RESPONSES = ["You're welcome!", "No problem!", "❤️"]

def sad_message(pet_name):
    return random.choice(SAD_MESSAGES) % {"pet_name": pet_name}


def a_an(noun):
    if noun == 'unicorn':
        return 'a ' + noun
    if noun[0] in "AaEeIiOoUu":
        return "an " + noun
    return "a " + noun


def position_tuple(pos):
    return (pos["x"], pos["y"])


def response_handler(commands, pattern):
    def decorator(f):
        commands.append((pattern, f))
        return f

    return decorator


async def reset_agency():
    async with rctogether.RestApiSession() as session:
        for bot in await rctogether.bots.get(session):
            if bot["emoji"] == "🧞":
                pass
            elif not bot.get("message"):
                print("Bot: ", bot)
                await rctogether.bots.delete(session, bot["id"])

class Pet(Bot):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.owner = None

    async def get_queued_update(self):
        if not self.owner:
            return await super().get_queued_update()

        try:
            update = await asyncio.wait_for(self.queue.get(), random.randint(*PET_BOREDOM_TIMES))
        except asyncio.TimeoutError:
            return {
                'x': random.randint(*CORRAL['x']),
                'y': random.randint(*CORRAL['y'])}

        while update is not None and not self.queue.empty():
            print("Skipping outdated update: ", update)
            update = await self.queue.get()

        return update


class Agency:
    """
        public interface:
            create (static)
                (session) -> Agency
            handle_entity
                (json_blob)
    """
    COMMANDS = []

    def __init__(self, session, genie, available_pets, owned_pets):
        self.session = session
        self.genie = genie
        self.available_pets = available_pets
        self.owned_pets = owned_pets
        self.processed_message_dt = datetime.datetime.utcnow()

    @classmethod
    async def create(cls, session):
        genie = None
        available_pets = {}
        owned_pets = defaultdict(list)

        for bot_json in await rctogether.bots.get(session):

            if bot_json["emoji"] == "🧞":
                genie = Bot(bot_json)
                genie.start_task(session)
                print("Found the genie: ", bot_json)
            else:
                pet = Pet(bot_json)

                if bot_json.get("message"):
                    owner_id = bot_json["message"]["mentioned_entity_ids"][0]
                    pet.owner = owner_id
                    owned_pets[owner_id].append(pet)
                else:
                    available_pets[position_tuple(bot_json["pos"])] = pet

                pet.start_task(session)

        if not genie:
            genie = await Bot.create(
                session,
                name=GENIE_NAME,
                emoji="🧞",
                x=GENIE_HOME["x"],
                y=GENIE_HOME["y"],
                can_be_mentioned=True,
            )

        agency = cls(session, genie, available_pets, owned_pets)
        return agency

    async def close(self):
        if self.genie:
            await self.genie.close()

        for pet in self.available_pets.values():
            await pet.close()

        for pet_collection in self.owned_pets.values():
            for pet in pet_collection:
                await pet.close()


    async def restock_inventory(self):
        for pos in SPAWN_POINTS:
            if position_tuple(pos) not in self.available_pets:
                self.available_pets[position_tuple(pos)] = await self.spawn_pet(
                    pos
                )

    async def spawn_pet(self, pos):
        pet = random.choice(PETS)
        while self.available(pet["emoji"]):
            pet = random.choice(PETS)

        return await Bot.create(
            self.session,
            name=pet["name"],
            emoji=pet["emoji"],
            x=pos["x"],
            y=pos["y"],
        )

    def available(self, pet):
        return any(x.emoji == pet for x in self.available_pets.values())

    def get_by_name(self, pet_name):
        for pet in self.available_pets.values():
            if pet.name == pet_name:
                return pet
        return None

    def get_random(self):
        return random.choice(list(self.available_pets.values()))

    def pop_owned_by_type(self, pet_name, owner):
        for pet in self.owned_pets[owner["id"]]:
            if pet.name.split(" ")[-1] == pet_name:
                self.owned_pets[owner["id"]].remove(pet)
                return pet
        return None

    def random_available_pet(self):
        return random.choice(list(self.available_pets.values()))

    def random_owned(self, owner):
        return random.choice(self.owned_pets[owner["id"]])

    async def send_message(self, recipient, message_text, sender=None):
        sender = sender or self.genie
        await rctogether.messages.send(
            self.session, sender.id, f"@**{recipient['person_name']}** {message_text}"
        )

    @response_handler(COMMANDS, "time to restock")
    async def handle_restock(self, adopter, match):
        await self.restock_inventory()
        return "New pets now in stock!"

    @response_handler(COMMANDS, "adopt (a|an|the|one)? ([A-Za-z-]+)")
    async def handle_adoption(self, adopter, match):
        if not any(please in match.string.lower() for please in MANNERS):
            return "No please? Our pets are only available to polite homes."

        pet_name = match.groups()[1]

        if pet_name == "horse":
            return "Sorry, that's just a picture of a horse."

        if pet_name == "genie":
            return "You can't adopt me. I'm not a pet!"

        if pet_name == "apatosaurus":
            return "Since 2015 the brontasaurus and apatosaurus have been recognised as separate species. Would you like to adopt a brontasaurus?"

        if pet_name == "pet":
            try:
                pet = self.get_random()
            except IndexError:
                return "Sorry, we don't have any pets at the moment, perhaps it's time to restock?"
        else:
            pet = self.get_by_name(pet_name)

        if not pet:
            try:
                alternative = self.random_available_pet().name
            except IndexError:
                return "Sorry, we don't have any pets at the moment, perhaps it's time to restock?"

            return f"Sorry, we don't have {a_an(pet_name)} at the moment, perhaps you'd like {a_an(alternative)} instead?"

        await self.send_message(adopter, NOISES.get(pet.emoji, "💖"), pet)
        await rctogether.bots.update(
            self.session,
            pet.id,
            {"name": f"{adopter['person_name']}'s {pet.name}"},
        )
        del self.available_pets[position_tuple(pet.bot_json["pos"])]
        self.owned_pets[adopter["id"]].append(pet)
        pet.owner = adopter["id"]

        return None

    @response_handler(COMMANDS, "thank")
    async def handle_thanks(self, adopter, match):
        return random.choice(THANKS_RESPONSES)

    @response_handler(COMMANDS, r"abandon my ([A-Za-z-]+)")
    async def handle_abandonment(self, adopter, match):
        pet_name = match.groups()[0]
        pet = self.pop_owned_by_type(pet_name, adopter)

        if not pet:
            try:
                suggested_alternative = self.random_owned(adopter).name.split(" ")[-1]
            except IndexError:
                return "Sorry, you don't have any pets to abandon, perhaps you'd like to adopt one?"
            return f"Sorry, you don't have {a_an(pet_name)}. Would you like to abandon your {suggested_alternative} instead?"

        await self.send_message(adopter, sad_message(pet_name), pet)
        await rctogether.bots.delete(self.session, pet.id)
        return None

    @response_handler(
        COMMANDS, r"well[- ]actually|feigning surprise|backseat driving|subtle[- ]*ism"
    )
    async def handle_social_rules(self, adopter, match):
        return "Oh, you're right. Sorry!"

    @response_handler(COMMANDS, r"help")
    async def handle_help(self, adopter, match):
        return """I can help you adopt a pet! Just send me a message saying 'adopt the <pet type> please'. The agency is just north of the main space. Drop by to see the available pets, and read more instructions on the note by the door."""

    async def handle_mention(self, adopter, message):
        for (pattern, handler) in self.COMMANDS:
            match = re.search(pattern, message["text"], re.IGNORECASE)
            if match:
                response = await handler(self, adopter, match)
                if response:
                    await self.send_message(adopter, response)
                return

        await self.send_message(
            adopter, "Sorry, I don't understand. Would you like to adopt a pet?"
        )

    async def handle_entity(self, entity):
        if entity["type"] == "Avatar":
            message = entity.get("message")

            if message and self.genie.id in message["mentioned_entity_ids"]:
                message_dt = datetime.datetime.strptime(
                    message["sent_at"], "%Y-%m-%dT%H:%M:%SZ"
                )
                if message_dt <= self.processed_message_dt:
                    print("Skipping old message: ", message)
                else:
                    await self.handle_mention(entity, message)
                    self.processed_message_dt = message_dt

        if entity["type"] == "Avatar":
            for pet in self.owned_pets.get(entity["id"], []):
                print(entity)
                position = offset_position(entity["pos"], random.choice(DELTAS))
                print(f"Moving {pet} to {position}")
                await pet.update(position)


DELTAS = [{"x": x, "y": y} for x in [-1, 0, 1] for y in [-1, 0, 1] if x != 0 or y != 0]


async def main():
    async with rctogether.RestApiSession() as session:
        agency = await Agency.create(session)

        async for entity in rctogether.WebsocketSubscription():
            await agency.handle_entity(entity)


if __name__ == "__main__":
    asyncio.run(main())
