import pytest
from collections import namedtuple

import pets
from bot import Bot

Post = namedtuple('Post', ('path', 'json'))

class MockSession:
    def __init__(self, get_data):
        self.posts = []
        self.get_data = get_data

    async def get(self, path):
        return self.get_data[path]

    async def post(self, path, json):
        self.posts.append(Post(path, json))
        return

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

    agency = pets.Agency.create(session)

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
