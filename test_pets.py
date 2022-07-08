import pytest
from collections import namedtuple
import asyncio

import pets
from bot import Bot

Post = namedtuple('Post', ('path', 'json'))
Patch = namedtuple('Patch', ('path', 'id', 'json'))

class MockSession:
    def __init__(self, get_data):
        self.posts = []
        self.patches = []
        self.get_data = get_data

    async def get(self, path):
        return self.get_data[path]

    async def post(self, path, json):
        self.posts.append(Post(path, json))
        return

    async def patch(self, path, bot_id, json):
        self.patches.append(Patch(path, bot_id, json))


@pytest.fixture
def genie():
    return {
        'type': 'Bot',
        'id': 1,
        'emoji': "🧞",
    }

@pytest.fixture
def rocket():
    return {
        'type': 'Bot',
        'id': 39887,
        'name': 'rocket',
        'emoji': "🚀",
        'pos': {'x': 1, 'y': 1}
    }

@pytest.fixture
def person():
    return {
        'type': 'Avatar',
        'id': 91,
        'person_name': 'Faker McFakeface',
        'pos': {'x': 15, 'y': 27}
    }

def incoming_message(sender, recipient, message):
    sender['message'] = {
            'mentioned_entity_ids': [recipient['id']],
            'sent_at': '2037-12-31T23:59:59Z', # More reasonable sent_at.
            'text': message
    }
    return sender

def response_text(recipient, message):
    message_text = message['text']
    mention = f"@**{recipient['person_name']}** "
    assert message_text[:len(mention)] == mention
    return message_text[len(mention):]

@pytest.mark.asyncio
async def test_thanks(genie, person):
    genie_id = genie['id']
    session = MockSession({
        "bots": [genie]
    })

    agency = await pets.Agency.create(session)

    await agency.handle_entity(incoming_message(person, genie, 'thanks!'))
    print(session.posts)
    message = session.posts[0].json
    print(message['text'])
    assert message['bot_id'] == genie_id
    assert response_text(person, message) in pets.THANKS_RESPONSES

    await agency.close()

@pytest.mark.asyncio
async def test_adopt_unavailable(genie, rocket, person):
    session = MockSession({
        "bots": [genie, rocket]
    })

    agency = await pets.Agency.create(session)

    await agency.handle_entity(incoming_message(person, genie, 'adopt the dog, please!'))

    message = session.posts[0].json
    assert message['bot_id'] == genie['id']
    assert response_text(person, message) == "Sorry, we don't have a dog at the moment, perhaps you'd like a rocket instead?"

    await agency.close()


@pytest.mark.asyncio
async def test_successful_adoption(genie, rocket, person):
    session = MockSession({
        "bots": [genie, rocket]
    })

    agency = await pets.Agency.create(session)

    await agency.handle_entity(incoming_message(person, genie, 'adopt the rocket, please!'))

    message = session.posts[0].json
    assert len(session.posts) == 1
    assert message['bot_id'] == rocket['id']
    assert response_text(person, message) == pets.NOISES["🚀"]

    # Sleep to make sure that the pet has a chance to move.
    # There should be a better approach than sleeping.
    await asyncio.sleep(0.01)

    assert session.patches[0] == Patch(path='bots', id=39887, json={'bot': {'name': f"{person['person_name']}'s rocket"}})

    location_update = session.patches[1]
    assert pets.is_adjacent(person['pos'], {'x': location_update.json['bot']['x'], 'y': location_update.json['bot']['y']})

    await agency.close()
