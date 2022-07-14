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


@pytest.fixture(name="genie")
def genie_fixture():
    return {"type": "Bot", "id": 1, "emoji": "🧞", "name": "Unit Genie"}


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


@pytest.fixture(name="owned_cat")
def owned_cat_fixture(person):
    return {
        "type": "Bot",
        "id": 39887,
        "name": "Faker McFaceface's cat",
        "emoji": "🐈",
        "pos": {"x": 1, "y": 1},
        "message": {"mentioned_entity_ids": [person["id"]]},
    }


@pytest.fixture(name="in_day_care_unicorn")
def in_day_care_unicorn_fixture(person):
    return {
        "type": "Bot",
        "id": 987,
        "name": "Faker McFaceface's unicorn",
        "emoji": "🦄",
        "pos": {"x": 6, "y": 70},
        "message": {"mentioned_entity_ids": [person["id"]]},
        "is_in_day_care_center": True,
    }


def incoming_message(sender, recipient, message):
    sender["message"] = {
        "mentioned_entity_ids": [recipient["id"]],
        "sent_at": "2037-12-31T23:59:59Z",  # More reasonable sent_at.
        "text": message,
    }
    return sender


def response_text(recipient, message):
    message_text = message["text"]
    mention = f"@**{recipient['person_name']}** "
    assert message_text[: len(mention)] == mention
    return message_text[len(mention) :]


@pytest.mark.asyncio
async def test_thanks(genie, person):
    genie_id = genie["id"]
    session = MockSession({"bots": [genie]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(incoming_message(person, genie, "thanks!"))

    request = await session.get_request()
    message = request.json
    assert message["bot_id"] == genie_id
    assert response_text(person, message) in pets.THANKS_RESPONSES


@pytest.mark.asyncio
async def test_adopt_unavailable(genie, rocket, person):
    session = MockSession({"bots": [genie, rocket]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "adopt the dog, please!")
        )

    request = await session.get_request()
    message = request.json
    assert message["bot_id"] == genie["id"]
    assert (
        response_text(person, message)
        == "Sorry, we don't have a dog at the moment, perhaps you'd like a rocket instead?"
    )


@pytest.mark.asyncio
async def test_successful_adoption(genie, rocket, person):
    session = MockSession({"bots": [genie, rocket]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "adopt the rocket, please!")
        )

    request = await session.get_request()
    message = request.json

    assert message["bot_id"] == rocket["id"]
    assert response_text(person, message) == pets.NOISES["🚀"]

    request = await session.get_request()

    assert request == Request(
        method="patch",
        path="bots",
        id=rocket["id"],
        json={"bot": {"name": f"{person['person_name']}'s rocket"}},
    )

    location_update = await session.get_request()
    assert pets.is_adjacent(person["pos"], location_update.json["bot"])


@pytest.mark.asyncio
async def test_successful_abandonment(genie, owned_cat, person):
    session = MockSession({"bots": [genie, owned_cat]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "I wish to heartlessly abandon my cat!")
        )

    request = await session.get_request()
    assert response_text(person, request.json) in [
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

    request = await session.get_request()
    assert response_text(person, request.json) == "miaow!"

    location_update = await session.get_request()
    new_position = location_update.json["bot"]
    assert pets.in_region(new_position, pets.DAY_CARE_CENTER)

    await asyncio.sleep(1)
    assert not session.pending_requests()


@pytest.mark.asyncio
async def test_successful_day_care_pick_up(genie, in_day_care_unicorn, person):
    session = MockSession({"bots": [genie, in_day_care_unicorn]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "Could I collect my unicorn, please?")
        )

    request = await session.get_request()
    assert response_text(person, request.json) == "✨"

    location_update = await session.get_request()
    assert pets.is_adjacent(person["pos"], location_update.json["bot"])


@pytest.mark.asyncio
async def test_wrong_pet_day_care_pick_up(genie, in_day_care_unicorn, person):
    session = MockSession({"bots": [genie, in_day_care_unicorn]})

    async with await pets.Agency.create(session) as agency:
        await agency.handle_entity(
            incoming_message(person, genie, "Could I collect my rocket, please?")
        )

    request = await session.get_request()
    assert (
        response_text(person, request.json)
        == "Sorry, you don't have a rocket to collect. Would you like to collect your unicorn instead?"
    )


@pytest.mark.asyncio
async def test_follow_owner(genie, owned_cat, person):
    session = MockSession({"bots": [genie, owned_cat]})

    async with await pets.Agency.create(session) as agency:
        person["pos"] = {"x": 50, "y": 45}
        await agency.handle_entity(person)

    location_update = await session.get_request()
    assert pets.is_adjacent(person["pos"], location_update.json["bot"])


@pytest.mark.asyncio
async def test_corral(owned_cat):
    pet = pets.Pet(owned_cat)

    assert pet.owner == 91

    await pet.update({"x": 2, "y": 3})

    updates = pet.queued_updates()
    assert await updates.__anext__() == {"x": 2, "y": 3}

    corral_move = await updates.__anext__()
    assert pets.in_region(corral_move, pets.CORRAL)

    await pet.update({"x": 8, "y": 9})
    assert await updates.__anext__() == {"x": 8, "y": 9}

    corral_move = await updates.__anext__()
    assert pets.in_region(corral_move, pets.CORRAL)

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
