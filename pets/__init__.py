import os
import random
import datetime
import textwrap

from collections import defaultdict
import logging
import asyncio
import time

import rctogether

from .parser import parse_command
from .update_queues import UpdateQueues
from . import update_queues

logging.basicConfig(level=logging.INFO)


def parse_position(position):
    x, y = position.split(",")
    return {"x": int(x), "y": int(y)}


def position_tuple(pos):
    return (pos["x"], pos["y"])


def offset_position(position, delta):
    return {"x": position["x"] + delta["x"], "y": position["y"] + delta["y"]}


def is_adjacent(p1, p2):
    return abs(p2["x"] - p1["x"]) <= 1 and abs(p2["y"] - p1["y"]) <= 1


class Region:
    def __init__(self, top_left, bottom_right):
        self.top_left = top_left
        self.bottom_right = bottom_right

    def __contains__(self, point):
        return (
            self.top_left["x"] <= point["x"] <= self.bottom_right["x"]
            and self.top_left["y"] <= point["y"] <= self.bottom_right["y"]
        )

    def random_point(self):
        return {
            "x": random.randint(self.top_left["x"], self.bottom_right["x"]),
            "y": random.randint(self.top_left["y"], self.bottom_right["y"]),
        }

    def __repr__(self):
        return f"<Region {self.top_left!r} {self.bottom_right!r}>"


HELP_TEXT = textwrap.dedent(
    """\
        I can help you adopt a pet! Just send me a message saying 'adopt the <pet type> please'.
        The agency is just north of the main space. Drop by to see the available pets, and read more instructions on the note by the door."""
)

PETS = [
    {"emoji": "🦇", "name": "bat", "noise": "screech!"},
    {"emoji": "🐻", "name": "bear", "noise": "ROAR!"},
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
    {"emoji": "🪨", "name": "rock", "noise": "🤘"},
]

NOISES = {pet["emoji"]: pet.get("noise", "💖") for pet in PETS}

GENIE_NAME = os.environ.get("GENIE_NAME", "Pet Agency Genie")
GENIE_HOME = parse_position(os.environ.get("GENIE_HOME", "60,15"))
SPAWN_POINTS = {
    position_tuple(offset_position(GENIE_HOME, {"x": dx, "y": dy}))
    for (dx, dy) in [(-2, -2), (0, -2), (2, -2), (-2, 0), (2, 0), (0, 2), (2, 2)]
}

CORRAL = Region({"x": 0, "y": 40}, {"x": 19, "y": 58})

PET_BOREDOM_TIMES = (3600, 5400)
LURE_TIME_SECONDS = 600
DAY_CARE_CENTER = Region({"x": 0, "y": 62}, {"x": 11, "y": 74})

SAD_MESSAGE_TEMPLATES = [
    "Was I not a good {pet_name}?",
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
    return random.choice(SAD_MESSAGE_TEMPLATES).format(pet_name=pet_name)


def a_an(noun):
    if noun == "unicorn":
        return "a " + noun
    if noun[0] in "AaEeIiOoUu":
        return "an " + noun
    return "a " + noun


def upfirst(text):
    return text[0].upper() + text[1:]


async def reset_agency():
    async with rctogether.RestApiSession() as session:
        for bot in await rctogether.bots.get(session):
            if bot["emoji"] == "🧞":
                pass
            elif not bot.get("message"):
                print("Bot: ", bot)
                await rctogether.bots.delete(session, bot["id"])


class Pet:
    def __init__(self, bot_json, *a, **k):
        self.bot_json = bot_json
        self.pos = bot_json["pos"]
        self.is_in_day_care_center = False
        if bot_json.get("message"):
            self.owner = bot_json["message"]["mentioned_entity_ids"][0]
            if "forget" in bot_json["message"]["text"]:
                self.is_in_day_care_center = True
        else:
            self.owner = None

    @classmethod
    async def create(cls, session, name, emoji, x, y, can_be_mentioned=False):
        bot_json = await rctogether.bots.create(
            session, name=name, emoji=emoji, x=x, y=y, can_be_mentioned=can_be_mentioned
        )
        return cls(bot_json)

    @property
    def type(self):
        return self.name.split(" ")[-1]

    @property
    def id(self):
        return self.bot_json["id"]

    @property
    def emoji(self):
        return self.bot_json["emoji"]

    @property
    def name(self):
        return self.bot_json["name"]


def owned_pet_name(owner, pet):
    return f"{owner['person_name']}'s {pet.type}"


class PetDirectory:
    def __init__(self):
        self._available_pets = {}
        self._owned_pets = defaultdict(list)
        self._pets_by_id = {}

    def add(self, pet):
        self._pets_by_id[pet.id] = pet

        if pet.owner:
            self._owned_pets[pet.owner].append(pet)
        else:
            self._available_pets[position_tuple(pet.pos)] = pet

    def remove(self, pet):
        del self._pets_by_id[pet.id]

        if pet.owner:
            self._owned_pets[pet.owner].remove(pet)
        else:
            del self._available_pets[position_tuple(pet.pos)]

    def available(self):
        return self._available_pets.values()

    def empty_spawn_points(self):
        return SPAWN_POINTS - set(self._available_pets.keys())

    def owned(self, owner_id):
        return self._owned_pets[owner_id]

    def __iter__(self):
        for pet in self._available_pets.values():
            yield pet

        yield from self.all_owned()

    def all_owned(self):
        for pet_collection in self._owned_pets.values():
            for pet in pet_collection:
                yield pet

    def __getitem__(self, pet_id):
        return self._pets_by_id[pet_id]

    def get(self, pet_id, default=None):
        return self._pets_by_id.get(pet_id, default)

    def set_owner(self, pet, owner):
        self.remove(pet)
        pet.owner = owner["id"]
        self.add(pet)


class AgencySync:
    def __init__(self, genie, pet_directory):
        self.pet_directory = pet_directory
        self.lured_pets_by_petter = defaultdict(list)
        self.lured_pets = {}
        self.avatars = {}

    def check_lured(self, pet):
        if pet.id not in self.lured_pets:
            return False

        if self.lured_pets[pet.id] < time.time():  # if timer is expired
            del self.lured_pets[pet.id]
            for petter_id in self.lured_pets_by_petter:
                for lured_pet in self.lured_pets_by_petter[petter_id]:
                    if lured_pet.id == pet.id:
                        self.lured_pets_by_petter[petter_id].remove(lured_pet)
            return False

        return True

    def handle_help(self, adopter, match):
        return HELP_TEXT

    def handle_adoption(self, adopter, match):
        if not any(please in match.string.lower() for please in MANNERS):
            return "No please? Our pets are only available to polite homes."

        pet_type = match.groups()[1]

        if pet_type == "horse":
            return "Sorry, that's just a picture of a horse."

        if pet_type == "genie":
            return "You can't adopt me. I'm not a pet!"

        if pet_type == "apatosaurus":
            return "Since 2015 the brontasaurus and apatosaurus have been recognised as separate species. Would you like to adopt a brontasaurus?"

        if pet_type == "pet":
            try:
                pet = random.choice(list(self.pet_directory.available()))
            except IndexError:
                return "Sorry, we don't have any pets at the moment, perhaps it's time to restock?"
        else:
            pet = get_one_by_type(pet_type, self.pet_directory.available())

        if not pet:
            try:
                alternative = random.choice(list(self.pet_directory.available())).name
            except IndexError:
                return "Sorry, we don't have any pets at the moment, perhaps it's time to restock?"

            return f"Sorry, we don't have {a_an(pet_type)} at the moment, perhaps you'd like {a_an(alternative)} instead?"

        self.pet_directory.set_owner(pet, adopter)

        return [
            ("send_message", adopter, NOISES.get(pet.emoji, "💖"), pet),
            ("sync_update_pet", pet, {"name": owned_pet_name(adopter, pet)}),
        ]

    def handle_abandon(self, adopter, match):
        pet_type = match.groups()[0]

        owned_pets = self.pet_directory.owned(adopter["id"])
        pet = get_one_by_type(pet_type, owned_pets)

        if not pet:
            if not owned_pets:
                return "Sorry, you don't have any pets to abandon, perhaps you'd like to adopt one?"
            suggested_alternative = random.choice(owned_pets).type
            return f"Sorry, you don't have {a_an(pet_type)}. Would you like to abandon your {suggested_alternative} instead?"

        self.pet_directory.remove(pet)

        return [
            ("send_message", adopter, sad_message(pet_type), pet),
            ("delete_pet", pet),
        ]

    def handle_thanks(self, adopter, match):
        return random.choice(THANKS_RESPONSES)

    def handle_social_rules(self, adopter, match):
        return "Oh, you're right. Sorry!"

    def handle_pet_a_pet(self, petter, match):
        # For the moment this command needs to be addressed to the genie (maybe won't later).
        # Find any pets next to the speaker of the right type.
        #  Do we have any pets of the right type next to the speaker?

        pet_type = match.group(1)

        for pet in self.pet_directory.all_owned():
            if is_adjacent(petter["pos"], pet.pos) and pet.type == pet_type:
                self.lured_pets[pet.id] = time.time() + LURE_TIME_SECONDS
                self.lured_pets_by_petter[petter["id"]].append(pet)

        return []

    def handle_give_pet(self, giver, match, mentioned_entities):
        pet_type = match.group(1)
        owned_pets = self.pet_directory.owned(giver["id"])
        pet = get_one_by_type(pet_type, owned_pets)

        if not pet:
            if not owned_pets:
                return "Sorry, you don't have any pets to give away, perhaps you'd like to adopt one?"

            suggested_alternative = random.choice(owned_pets).type

            return f"Sorry, you don't have {a_an(pet_type)}. Would you like to give your {suggested_alternative} instead?"

        if not mentioned_entities:
            return f"Who to you want to give your {pet_type} to?"
        recipient = self.avatars.get(mentioned_entities[0])

        if not recipient:
            return "Sorry, I don't know who that is! (Are they online?)"

        self.pet_directory.set_owner(pet, recipient)
        position = offset_position(recipient["pos"], random.choice(DELTAS))

        return [
            ("send_message", recipient, NOISES.get(pet.emoji, "💖"), pet),
            ("sync_update_pet", pet, {"name": owned_pet_name(recipient, pet)}),
            ("update_pet", pet, position),
        ]

    def handle_day_care_drop_off(self, owner, match):
        pet_type = match.groups()[0]

        pets_not_in_day_care = [
            pet
            for pet in self.pet_directory.owned(owner["id"])
            if not pet.is_in_day_care_center
        ]

        pet = get_one_by_type(pet_type, pets_not_in_day_care)

        if not pet:
            if not pets_not_in_day_care:
                return "Sorry, you don't have any pets to drop off, perhaps you'd like to adopt one?"
            suggested_alternative = random.choice(pets_not_in_day_care).type
            return f"Sorry, you don't have {a_an(pet_type)}. Would you like to drop off your {suggested_alternative} instead?"

        position = DAY_CARE_CENTER.random_point()
        pet.is_in_day_care_center = True

        return [
            ("send_message", owner, "Please don't forget about me!", pet),
            ("update_pet", pet, position),
        ]
        return None

    def handle_day_care_pick_up(self, owner, match):
        pet_type = match.groups()[0]

        pets_in_day_care = [
            pet
            for pet in self.pet_directory.owned(owner["id"])
            if pet.is_in_day_care_center
        ]

        pet = get_one_by_type(pet_type, pets_in_day_care)

        if not pet:
            if not pets_in_day_care:
                return "Sorry, you have no pets in day care. Would you like to drop one off?"
            suggested_alternative = random.choice(pets_in_day_care).type
            return f"Sorry, you don't have {a_an(pet_type)} to collect. Would you like to collect your {suggested_alternative} instead?"

        pet.is_in_day_care_center = False

        return [
            ("send_message", owner, NOISES.get(pet.emoji, "💖"), pet),
        ]

    def handle_avatar_move(self, entity):
        for pet in self.lured_pets_by_petter.get(entity["id"], []):
            position = offset_position(entity["pos"], random.choice(DELTAS))
            yield ("update_pet", pet, position)

        for pet in self.pet_directory.owned(entity["id"]):
            if pet.is_in_day_care_center or self.check_lured(pet):
                pet_update = {}
            else:
                pet_update = offset_position(entity["pos"], random.choice(DELTAS))

            # Handle possible name change.
            pet_name = owned_pet_name(entity, pet)
            if pet.name != pet_name:
                pet_update["name"] = pet_name

            if pet_update:
                yield ("update_pet", pet, pet_update)

    def handle_restock(self, restocker, match):
        actions = []

        if self.pet_directory.empty_spawn_points():
            pet = min(
                self.pet_directory.available(), key=lambda pet: pet.id, default=None
            )
            if pet:
                self.pet_directory.remove(pet)
                yield ("delete_pet", pet)
                yield (
                    "send_message",
                    restocker,
                    f"{upfirst(a_an(pet.type))} was unwanted and has been sent to the farm.",
                )

        for pos in self.pet_directory.empty_spawn_points():
            yield ("create_pet", pos)
            # pet = await self.spawn_pet(pos)
            # self.pet_directory.add(pet)
        yield "New pets now in stock!"

    def handle_created(self, pet):
        self.pet_directory.add(pet)

    def handle_bot(self, entity):
        try:
            pet = self.pet_directory[entity["id"]]
        except KeyError:
            pass
        else:
            pet.pos = entity["pos"]
            pet.bot_json["name"] = entity["name"]


class Agency:
    """
    public interface:
        create (static)
            (session) -> Agency
        handle_entity
            (json_blob)
    """

    def __init__(self, session, genie, pet_directory):
        self.session = session
        self.genie = genie
        self.pet_directory = pet_directory
        self.processed_message_dt = datetime.datetime.utcnow()
        self.agency_sync = AgencySync(genie, pet_directory)

        self._pet_update_queues = UpdateQueues(self.queue_iterator)

    @property
    def lured_pets(self):
        return self.agency_sync.lured_pets

    @property
    def lured_pets_by_petter(self):
        return self.agency_sync.lured_pets_by_petter

    @property
    def avatars(self):
        return self.agency_sync.avatars

    def __getattr__(self, name):
        return self.agency_sync.__getattribute__(name)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    @classmethod
    async def create(cls, session):
        genie = None
        pet_directory = PetDirectory()

        for bot_json in await rctogether.bots.get(session):
            if bot_json["emoji"] == "🧞":
                genie = Pet(bot_json)
                print("Found the genie: ", bot_json)
            else:
                pet = Pet(bot_json)
                pet_directory.add(pet)

        if not genie:
            genie = await Pet.create(
                session,
                name=GENIE_NAME,
                emoji="🧞",
                x=GENIE_HOME["x"],
                y=GENIE_HOME["y"],
                can_be_mentioned=True,
            )

        agency = cls(session, genie, pet_directory)
        return agency

    async def update_pet(self, pet, update):
        await self._pet_update_queues.add_task(
            pet.id, rctogether.bots.update(self.session, pet.id, update)
        )

    async def queue_iterator(self, queue, pet_id):
        pet = self.pet_directory.get(pet_id)

        updates = update_queues.deduplicated_updates(queue)

        while True:
            next_update = asyncio.Task(updates.__anext__())
            while True:
                try:
                    update = await asyncio.wait_for(
                        asyncio.shield(next_update),
                        timeout=random.randint(*PET_BOREDOM_TIMES),
                    )
                    yield update
                    break
                except asyncio.TimeoutError:
                    if pet and pet.owner and not pet.is_in_day_care_center:
                        yield CORRAL.random_point()
                except StopAsyncIteration:
                    return

    async def delete_pet(self, pet):
        await self._pet_update_queues.add_task(pet.id, None)
        await rctogether.bots.delete(self.session, pet.id)

    async def close(self):
        await self._pet_update_queues.close()

    async def spawn_pet(self, pos):
        pet = random.choice(PETS)
        while any(x.emoji == pet["emoji"] for x in self.pet_directory.available()):
            pet = random.choice(PETS)

        return await Pet.create(
            self.session,
            name=pet["name"],
            emoji=pet["emoji"],
            x=pos[0],
            y=pos[1],
        )

    async def send_message(self, recipient, message_text, sender=None):
        sender = sender or self.genie
        await rctogether.messages.send(
            self.session, sender.id, f"@**{recipient['person_name']}** {message_text}"
        )

    def handle_command(self, command, adopter, match, mentioned_entities):
        handler = getattr(self, f"handle_{command}")
        if command == "give_pet":
            return handler(adopter, match, mentioned_entities)
        return handler(adopter, match)

    async def handle_mention(self, adopter, message, mentioned_entity_ids):
        parsed = parse_command(message["text"])

        if not parsed:
            await self.send_message(
                adopter, "Sorry, I don't understand. Would you like to adopt a pet?"
            )
            return
        command, match = parsed

        mentioned_entity_ids = [x for x in mentioned_entity_ids if x != self.genie.id]

        task = self.handle_command(command, adopter, match, mentioned_entity_ids)

        if isinstance(task, str):
            task = [task]

        for event in task:
            if isinstance(event, str):
                event = ("send_message", adopter, event)

            await self.apply_event(event)

    async def apply_event(self, event):
        match event[0]:
            case "send_message":
                await self.send_message(*event[1:])
            case "update_pet":
                await self.update_pet(*event[1:])
            case "sync_update_pet":
                await rctogether.bots.update(self.session, event[1].id, event[2])
            case "delete_pet":
                await self.delete_pet(event[1])
            case "create_pet":
                pet = await self.spawn_pet(event[1])
                self.agency_sync.handle_created(pet)
            case _:
                raise ValueError(f"Unknown event: {event}")

    async def handle_entity(self, entity):
        if entity["type"] == "Avatar":
            self.avatars[entity["id"]] = entity

            message = entity.get("message")

            if message and self.genie.id in message["mentioned_entity_ids"]:
                message_dt = datetime.datetime.strptime(
                    message["sent_at"], "%Y-%m-%dT%H:%M:%SZ"
                )
                if message_dt > self.processed_message_dt:
                    await self.handle_mention(
                        entity, message, message["mentioned_entity_ids"]
                    )
                    self.processed_message_dt = message_dt

        if entity["type"] == "Avatar":
            for event in self.handle_avatar_move(entity):
                await self.apply_event(event)

        if entity["type"] == "Bot":
            self.handle_bot(entity)


def get_one_by_type(pet_type, pets):
    return next(iter(pet for pet in pets if pet_type == pet.type), None)


DELTAS = [{"x": x, "y": y} for x in [-1, 0, 1] for y in [-1, 0, 1] if x != 0 or y != 0]
