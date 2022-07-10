import pytest
from collections import namedtuple

import pets
from bot import Bot

Post = namedtuple('Post', ('path', 'json'))

class MockSession:
    def __init__(self):
        self.posts = []

    async def post(self, path, json):
        self.posts.append(Post(path, json))
        return

@pytest.mark.asyncio
async def test_thanks():
    session = MockSession()

    genie_id = 178
    genie = Bot({'id': genie_id})
    available_animals = {}
    owned_animals = {}

    agency = pets.Agency(session, genie, available_animals, owned_animals)

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
