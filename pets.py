import eventlet
eventlet.monkey_patch()

import random
import re
import datetime
from collections import defaultdict
import rctogether

ANIMALS = [
        {'emoji': '🐕', 'name': 'dog', 'noise': 'woof!'},
        {'emoji': '🐈', 'name': 'cat', 'noise': 'miaow!'},
        {'emoji': '🐁', 'name': 'mouse', 'noise': 'squeak!'},
        {'emoji': '🦛', 'name': 'hippo'},
        {'emoji': '🐸', 'name': 'frog', 'noise': 'ribbet!'},
        {'emoji': '🦖', 'name': 't-rex', 'noise': 'RAWR!'},
        {'emoji': '🦜', 'name': 'parrot', 'noise': 'HELLO!'},
        {'emoji': '🐊', 'name': 'crocodile'},
        {'emoji': '🦒', 'name': 'giraffe'},
        {'emoji': '🦆', 'name': 'duck', 'noise': 'quack!'},
        {'emoji': '🐑', 'name': 'sheep', 'noise': 'baa!'},
        {'emoji': '🐢', 'name': 'turtle'},
        {'emoji': '🐘', 'name': 'elephant'},
        {'emoji': '🚀', 'name': 'rocket'},
        ]

NOISES = {animal['emoji']: animal.get('noise', '💖') for animal in ANIMALS}

GENIE_HOME = {'x': 60, 'y': 15}
SPAWN_POINTS = [
        {'x': 58, 'y': 15},
        {'x': 58, 'y': 13},
        {'x': 60, 'y': 13},
        {'x': 62, 'y': 13},
        {'x': 62, 'y': 15},
        {'x': 62, 'y': 17},
        {'x': 60, 'y': 17},
    ]


    # print(entity)

def position_tuple(pos):
    return (pos['x'], pos['y'])

class Agency:
    def __init__(self):
        self.genie = None
        self.available_animals = {}
        self.owned_animals = defaultdict(list)
        self.processed_message_dt = datetime.datetime.utcnow()

        for bot in rctogether.get_bots():
            if bot['emoji'] == "🧞":
                print("Found the genie!")
                self.genie = rctogether.Bot(bot, print)
            else:
                if bot.get('message'):
                    [owner_id] = bot['message']['mentioned_entity_ids']
                    self.owned_animals[owner_id].append(rctogether.Bot(bot, print))
                else:
                    self.available_animals[position_tuple(bot['pos'])] = rctogether.Bot(bot, print)

    def restock_inventory(self):
        if not self.genie:
            raise ValueError("No genie!")
            self.genie = subscription.create_bot(
                name="Pet Agency Genie",
                emoji="🧞",
                x=GENIE_HOME['x'],
                y=GENIE_HOME['y'],
                can_be_mentioned=True,
                handle_update=print)

        for pos in SPAWN_POINTS:
            if position_tuple(pos) not in self.available_animals:
                self.available_animals[position_tuple(pos)] = self.spawn_animal(pos)

    def spawn_animal(self, pos):
        animal = random.choice(ANIMALS)
        while self.available(animal['emoji']):
            animal = random.choice(ANIMALS)

        return subscription.create_bot(
            name=animal['name'],
            emoji=animal['emoji'],
            x=pos['x'],
            y=pos['y'],
            handle_update=print)

    def available(self, animal):
        return any(x.emoji == animal for x in self.available_animals.values())

    def get_by_name(self, animal_name):
        for animal in self.available_animals.values():
            if animal.name == animal_name:
                return animal
        return None

    def random_available_animal(self):
        return random.choice(list(self.available_animals.values()))

    def handle_mention(self, adopter, message):
        print(message)
        m = re.search(r'adopt (a|an|the|one)? ([A-Za-z-]+),? please', message['text'])
        if m:
            animal_name = m.groups()[1]
            animal = self.get_by_name(animal_name)
            if not animal:
                rctogether.send_message(self.genie.id, f"@**{adopter['person_name']}** Sorry, we don't have a {animal_name} at the moment, perhaps you'd like a {self.random_available_animal().name} instead?")
                print("No such animal!")
                return
            print(animal)
            rctogether.send_message(animal.id, f"@**{adopter['person_name']}** {NOISES.get(animal.emoji, '💖')}")
            rctogether.update_bot(animal.id, {'name': f"{adopter['person_name']}'s {animal.name}"})
            del self.available_animals[position_tuple(animal.bot_json["pos"])]
           #  self.available_animals[position_tuple(animal.bot_json["pos"])] = self.spawn_animal(animal['pos'])
            self.owned_animals[adopter['id']].append(animal)

            print("owned_animals: ", self.owned_animals)

    def handle_entity(self, entity):
        if entity['type'] == 'Avatar':
            message = entity.get('message')

            if message and self.genie.id in message['mentioned_entity_ids']:
                message_dt = datetime.datetime.strptime(message['sent_at'], "%Y-%m-%dT%H:%M:%SZ")
                if message_dt <= self.processed_message_dt:
                    print("Skipping old message: ", message)
                else:
                    self.handle_mention(entity, message)
                    self.processed_message_dt = message_dt

        if entity['type'] == 'Avatar':
            for animal in self.owned_animals.get(entity['id'], []):
                print(entity)
                position = offset_position(entity['pos'], random.choice(DELTAS))
                print(f"Moving {animal} to {position}")
                animal.update(position)

        if entity['type'] in ('Avatar', 'Wall', 'Note', 'Desk', 'Bot', 'ZoomLink', 'AudioRoom', 'AudioBlock', 'RC::Calendar', 'Link'):
            return


DELTAS = [{'x': x, 'y': y} for x in [-1, 0, 1] for y in [-1, 0, 1] if x != 0 or y != 0]
def offset_position(position, delta):
    return {'x': position['x'] + delta['x'], 'y': position['y'] + delta['y']}

# rctogether.clean_up_bots()

agency = Agency()
subscription = rctogether.RcTogether(callbacks=[agency.handle_entity])
# agency.restock_inventory()
subscription.block_until_done()
