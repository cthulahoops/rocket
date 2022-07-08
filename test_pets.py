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


@pytest.mark.asyncio
async def test_thanks():
    genie_id = 178
    session = MockSession({
        "bots": [{
            'type': 'Bot',
            'id': genie_id,
            'emoji': "🧞",
        }]
    })

    agency = await pets.Agency.create(session)

    await agency.handle_entity({
        'type': 'Avatar',
        'id': 91,
        'person_name': 'Person Name',
        'message': {
            'mentioned_entity_ids': [genie_id],
            'sent_at': '2037-12-31T23:59:59Z', # More reasonable sent_at.
            'text': 'thanks!'
        }})
    print(session.posts)
    message = session.posts[0].json
    print(message['text'])
    assert message['bot_id'] == genie_id
    assert message['text'][len('@**Person Name** '):] in pets.THANKS_RESPONSES

@pytest.mark.asyncio
async def test_adopt_unavailable():
    genie_id = 178

    session = MockSession({
        "bots": [{
            'type': 'Bot',
            'id': genie_id,
            'emoji': "🧞",
        },
        {
            'type': 'Bot',
            'id': 39887,
            'name': 'rocket',
            'emoji': "🚀",
            'pos': {'x': 1, 'y': 1}
         }]
    })

    agency = await pets.Agency.create(session)

    await agency.handle_entity({
        'type': 'Avatar',
        'id': 91,
        'person_name': 'Person Name',
        'message': {
            'mentioned_entity_ids': [genie_id],
            'sent_at': '2037-12-31T23:59:59Z', # More reasonable sent_at.
            'text': 'adopt the dog, please!'
        }})
    print(session.posts)
    message = session.posts[0].json
    print(message['text'])
    assert message['bot_id'] == genie_id
    assert message['text'][len('@**Person Name** '):] == "Sorry, we don't have a dog at the moment, perhaps you'd like a rocket instead?"


@pytest.mark.asyncio
async def test_successful_adoption():
    genie_id = 178
    rocket_id = 39887

    session = MockSession({
        "bots": [{
            'type': 'Bot',
            'id': genie_id,
            'emoji': "🧞",
        },
        {
            'type': 'Bot',
            'id': rocket_id,
            'name': 'rocket',
            'emoji': "🚀",
            'pos': {'x': 1, 'y': 1}
         }]
    })

    agency = await pets.Agency.create(session)

    await agency.handle_entity({
        'type': 'Avatar',
        'id': 91,
        'person_name': 'Person Name',
        'message': {
            'mentioned_entity_ids': [genie_id],
            'sent_at': '2037-12-31T23:59:59Z', # More reasonable sent_at.
            'text': 'adopt the rocket, please!'
        },
        'pos': {'x': 5, 'y': 7}})
    message = session.posts[0].json
    assert len(session.posts) == 1
    assert message['bot_id'] == rocket_id
    assert message['text'][len('@**Person Name** '):] == pets.NOISES["🚀"]

    # Sleep to make sure that the pet has a chance to move.
    # There should be a better approach than sleeping.
    await asyncio.sleep(0.01)

    assert session.patches[0] == Patch(path='bots', id=39887, json={'bot': {'name': "Person Name's rocket"}})
    pos = pets.is_adjacent({'x': 5, 'y': 7}, {'x': session.patches[1].json['bot']['x'], 'y': session.patches[1].json['bot']['y']})
