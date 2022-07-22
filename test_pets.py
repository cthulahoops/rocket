from collections import namedtuple
import asyncio

import pytest

import pets
import bot

# Reduce the sleep delay in the bot update code so tests run faster.
bot.SLEEP_AFTER_UPDATE = 0.01
pets.PET_BOREDOM_TIMES = (1, 1)

Request = namedtuple("Request", ("method", "path", "id", "json"))


class MockSession:
    def __init__(self, get_data):
        self._queue = asyncio.Queue()
        self.get_data = get_data

    async def get(self, path):
        return self.get_data[path]

    async def post(self, path, json):
        await self._queue.put(Request("post", path, None, json))

    async def patch(self, path, bot_id, json):
        await self._queue.put(Request("patch", path, bot_id, json))

    async def delete(self, path, bot_id):
        await self._queue.put(Request("delete", path, bot_id, None))

    async def get_request(self):
        return await asyncio.wait_for(self._queue.get(), 0.1)

    def pending_requests(self):
        return not self._queue.empty()

    async def message_received(self, sender, recipient):
        request = await self.get_request()
        message = request.json
        assert message["bot_id"] == sender["id"]
        message_text = message["text"]
        mention = f"@**{recipient['person_name']}** "
        assert message_text[: len(mention)] == mention
        return message_text[len(mention) :]

    async def moved_to(self):
        request = await self.get_request()
        return request.json["bot"]


@pytest.fixture(name="genie")
def genie_fixture():
    return {
        "type": "Bot",
        "id": 1,
        "emoji": "🧞",
        "name": "Unit Genie",
        "pos": {"x": -7, "y": -9},
    }


@pytest.fixture(name="rocket")
def rocket_fixture():
    return {
        "type": "Bot",
        "id": 39887,
        "name": "rocket",
        "emoji": "🚀",
        "pos": {"x": 1, "y": 1},
    }


@pytest.fixture(name="person")
def person_fixture():
    return {
        "type": "Avatar",
        "id": 91,
        "person_name": "Faker McFakeface",
        "pos": {"x": 15, "y": 27},
    }


@pytest.fixture(name="petless_person")
def petless_person_fixture():
    return {
        "type": "Avatar",
        "id": 81,
        "person_name": "Petless McPetface",
        "pos": {"x": 20, "y": 20},
    }


@pytest.fixture(name="owned_cat")
def owned_cat_fixture(person):
    return {
        "type": "Bot",
        "id": 39887,
        "name": "Faker McFaceface's cat",
        "emoji": "🐈",
        "pos": {"x": 1, "y": 1},
        "message": {
            "mentioned_entity_ids": [person["id"]],
            "text": "@**Faker McFaceface** miaow!",
        },
    }


@pytest.fixture(name="in_day_care_unicorn")
def in_day_care_unicorn_fixture(person):
    return {
        "type": "Bot",
        "id": 987,
        "name": "Faker McFaceface's unicorn",
        "emoji": "🦄",
        "pos": {"x": 6, "y": 70},
        "message": {
            "mentioned_entity_ids": [person["id"]],
            "text": "@**Faker McFaceface** please don't forget about me!",
        },
    }


def incoming_message(sender, recipient, message):
    sender["message"] = {
        "mentioned_entity_ids": [recipient["id"]],
        "sent_at": "2037-12-31T23:59:59Z",  # More reasonable sent_at.
        "text": message,
    }
    return sender


@pytest.mark.asyncio
async def test_thanks(genie, person):
    session = MockSession({"bots": [genie]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(incoming_message(person, genie, "thanks!"))

    assert await session.message_received(genie, person) in pets.THANKS_RESPONSES


@pytest.mark.asyncio
async def test_adopt_unavailable(genie, rocket, person):
    session = MockSession({"bots": [genie, rocket]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "adopt the dog, please!")
        )

    assert (
        await session.message_received(genie, person)
        == "Sorry, we don't have a dog at the moment, perhaps you'd like a rocket instead?"
    )


@pytest.mark.asyncio
async def test_successful_adoption(genie, rocket, person):
    session = MockSession({"bots": [genie, rocket]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "adopt the rocket, please!")
        )

    assert await session.message_received(rocket, person) == pets.NOISES["🚀"]

    request = await session.get_request()

    assert request == Request(
        method="patch",
        path="bots",
        id=rocket["id"],
        json={"bot": {"name": f"{person['person_name']}'s rocket"}},
    )

    assert pets.is_adjacent(person["pos"], await session.moved_to())


@pytest.mark.asyncio
async def test_successful_abandonment(genie, owned_cat, person):
    session = MockSession({"bots": [genie, owned_cat]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "I wish to heartlessly abandon my cat!")
        )

    assert await session.message_received(owned_cat, person) in [
        template.format(pet_name="cat") for template in pets.SAD_MESSAGE_TEMPLATES
    ]

    request = await session.get_request()
    assert request == Request(
        method="delete", path="bots", id=owned_cat["id"], json=None
    )


@pytest.mark.asyncio
async def test_successful_day_care_drop_off(genie, owned_cat, person):
    session = MockSession({"bots": [genie, owned_cat]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "Please look after my cat!")
        )
        person["pos"] = {"x": 50, "y": 45}
        await agency.handle_entity(person)

    assert (
        await session.message_received(owned_cat, person)
        == "Please don't forget about me!"
    )

    assert await session.moved_to() in pets.DAY_CARE_CENTER

    await asyncio.sleep(1)
    assert not session.pending_requests()


@pytest.mark.asyncio
async def test_successful_day_care_pick_up(genie, in_day_care_unicorn, person):
    session = MockSession({"bots": [genie, in_day_care_unicorn]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "Could I collect my unicorn, please?")
        )

    assert await session.message_received(in_day_care_unicorn, person) == "✨"

    assert pets.is_adjacent(person["pos"], await session.moved_to())


@pytest.mark.asyncio
async def test_wrong_pet_day_care_pick_up(genie, in_day_care_unicorn, person):
    session = MockSession({"bots": [genie, in_day_care_unicorn]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "Could I collect my rocket, please?")
        )

    assert (
        await session.message_received(genie, person)
        == "Sorry, you don't have a rocket to collect. Would you like to collect your unicorn instead?"
    )


@pytest.mark.asyncio
async def test_follow_owner(genie, owned_cat, person):
    session = MockSession({"bots": [genie, owned_cat]})

    async with await pets.Agency.create(session) as agency:
        person["pos"] = {"x": 50, "y": 45}
        await agency.handle_entity(person)

    assert pets.is_adjacent(person["pos"], await session.moved_to())


@pytest.mark.asyncio
async def test_corral(owned_cat):
    pet = pets.Pet(owned_cat)

    assert pet.owner == 91

    await pet.update({"x": 2, "y": 3})

    updates = pet.queued_updates()
    assert await updates.__anext__() == {"x": 2, "y": 3}

    corral_move = await updates.__anext__()
    assert corral_move in pets.CORRAL

    await pet.update({"x": 8, "y": 9})
    assert await updates.__anext__() == {"x": 8, "y": 9}

    corral_move = await updates.__anext__()
    assert corral_move in pets.CORRAL

    await pet.update(None)
    with pytest.raises(StopAsyncIteration):
        await updates.__anext__()


@pytest.mark.asyncio
async def test_unowned_pets_dont_escape(rocket):
    pet = pets.Pet(rocket)

    assert pet.owner is None

    await pet.update({"x": 2, "y": 3})

    updates = pet.queued_updates()
    assert await updates.__anext__() == {"x": 2, "y": 3}
    await asyncio.sleep(1.5)

    await pet.update({"x": 8, "y": 9})
    assert await updates.__anext__() == {"x": 8, "y": 9}

    await pet.update(None)
    with pytest.raises(StopAsyncIteration):
        await updates.__anext__()


@pytest.mark.asyncio
async def test_pet_a_pet(genie, owned_cat, petless_person, person):
    session = MockSession({"bots": [genie, owned_cat]})
    pets.LURE_TIME_SECONDS = 600

    async with await pets.Agency.create(session) as agency:
        petless_person["pos"] = {"x": 1, "y": 2}  # Cat is at 1,1 - this is adjacent.
        await agency.handle_entity(petless_person)
        await agency.handle_entity(
            incoming_message(petless_person, genie, "Pet the cat!")
        )
        petless_person["pos"] = {"x": 21, "y": 30}
        await agency.handle_entity(petless_person)

        # Rightful owner should be ignored
        person["pos"] = {"x": 99, "y": 99}
        await agency.handle_entity(person)

    pet_position = await session.moved_to()
    assert pets.is_adjacent(petless_person["pos"], pet_position)


@pytest.mark.asyncio
async def test_pet_a_pet_with_pet_move(genie, owned_cat, petless_person, person):
    session = MockSession({"bots": [genie, owned_cat]})
    pets.LURE_TIME_SECONDS = 600

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            {"type": "Bot", "id": owned_cat["id"], "pos": {"x": 99, "y": 108}}
        )
        petless_person["pos"] = {
            "x": 100,
            "y": 108,
        }
        await agency.handle_entity(petless_person)
        await agency.handle_entity(
            incoming_message(petless_person, genie, "Pet the cat!")
        )
        petless_person["pos"] = {"x": 21, "y": 30}
        await agency.handle_entity(petless_person)

        # Rightful owner should be ignored
        person["pos"] = {"x": 99, "y": 99}
        await agency.handle_entity(person)

    pet_position = await session.moved_to()
    assert pets.is_adjacent(petless_person["pos"], pet_position)


@pytest.mark.asyncio
async def test_pet_a_pet_expired(genie, owned_cat, petless_person, person):
    session = MockSession({"bots": [genie, owned_cat]})
    pets.LURE_TIME_SECONDS = -1

    async with await pets.Agency.create(session) as agency:
        petless_person["pos"] = {"x": 1, "y": 2}  # Cat is at 1,1 - this is adjacent.
        await agency.handle_entity(petless_person)
        await agency.handle_entity(
            incoming_message(petless_person, genie, "Pet the cat!")
        )
        petless_person["pos"] = {"x": 21, "y": 30}
        await agency.handle_entity(petless_person)

        # Rightful owner should not be ignored: timer is expired
        person["pos"] = {"x": 99, "y": 99}
        await agency.handle_entity(person)
        petless_person["pos"] = {"x": 21, "y": 30}
        await agency.handle_entity(petless_person)

    pet_position = await session.moved_to()
    assert pets.is_adjacent(person["pos"], pet_position)
