import random
import re
import datetime
from collections import defaultdict

import eventlet

eventlet.monkey_patch()

import rctogether  # pylint: disable=wrong-import-position

ANIMALS = [
    {"emoji": "🐕", "name": "dog", "noise": "woof!"},
    {"emoji": "🐈", "name": "cat", "noise": "miaow!"},
    {"emoji": "🐁", "name": "mouse", "noise": "squeak!"},
    {"emoji": "🦛", "name": "hippo"},
    {"emoji": "🐸", "name": "frog", "noise": "ribbet!"},
    {"emoji": "🦖", "name": "t-rex", "noise": "RAWR!"},
    {"emoji": "🦜", "name": "parrot", "noise": "HELLO!"},
    {"emoji": "🐊", "name": "crocodile"},
    {"emoji": "🦒", "name": "giraffe"},
    {"emoji": "🦆", "name": "duck", "noise": "quack!"},
    {"emoji": "🐑", "name": "sheep", "noise": "baa!"},
    {"emoji": "🐢", "name": "turtle"},
    {"emoji": "🐘", "name": "elephant"},
    {"emoji": "🦉", "name": "owl", "noise": "hoot hoot!"},
    {"emoji": "🐉", "name": "dragon", "noise": "🔥"},
    {"emoji": "🚀", "name": "rocket"},
    {"emoji": "🦊", "name": "fox", "noise": "Wrahh!"},
    {"emoji": "🐌", "name": "snail", "noise": "slurp!"}
]

NOISES = {animal["emoji"]: animal.get("noise", "💖") for animal in ANIMALS}

GENIE_HOME = {"x": 60, "y": 15}
SPAWN_POINTS = [
    {"x": 58, "y": 15},
    {"x": 58, "y": 13},
    {"x": 60, "y": 13},
    {"x": 62, "y": 13},
    {"x": 62, "y": 15},
    {"x": 62, "y": 17},
    {"x": 60, "y": 17},
]

SAD_MESSAGES = [
        "Was I not a good %(animal_name)s?",
        "I thought you liked me.",
        "😢",
        "What will I do now?",
        "But where will I go?",
        "But why?"
        "💔"]

def sad_message(animal_name):
    return random.choice(SAD_MESSAGES) % {'animal_name': animal_name}

def a_an(noun):
    if noun[0] in "AaEeIiOoUu":
        return "an " + noun
    return "a " + noun


def position_tuple(pos):
    return (pos["x"], pos["y"])


class Agency:
    def __init__(self):
        self.genie = None
        self.available_animals = {}
        self.owned_animals = defaultdict(list)
        self.processed_message_dt = datetime.datetime.utcnow()

        for bot in rctogether.get_bots():
            if bot["emoji"] == "🧞":
                print("Found the genie!")
                self.genie = rctogether.Bot(bot, print)
            else:
                if bot.get("message"):
                    owner_id = bot["message"]["mentioned_entity_ids"][0]
                    self.owned_animals[owner_id].append(rctogether.Bot(bot, print))
                else:
                    self.available_animals[position_tuple(bot["pos"])] = rctogether.Bot(
                        bot, print
                    )

    def restock_inventory(self):
        if not self.genie:
            self.genie = subscription.create_bot(
                name="Pet Agency Genie",
                emoji="🧞",
                x=GENIE_HOME["x"],
                y=GENIE_HOME["y"],
                can_be_mentioned=True,
                handle_update=print,
            )

        for pos in SPAWN_POINTS:
            if position_tuple(pos) not in self.available_animals:
                self.available_animals[position_tuple(pos)] = self.spawn_animal(pos)

    def spawn_animal(self, pos):
        animal = random.choice(ANIMALS)
        while self.available(animal["emoji"]):
            animal = random.choice(ANIMALS)

        return subscription.create_bot(
            name=animal["name"],
            emoji=animal["emoji"],
            x=pos["x"],
            y=pos["y"],
            handle_update=print,
        )

    def available(self, animal):
        return any(x.emoji == animal for x in self.available_animals.values())

    def get_by_name(self, animal_name):
        for animal in self.available_animals.values():
            if animal.name == animal_name:
                return animal
        return None

    def pop_owned_by_type(self, animal_name, owner):
        for animal in self.owned_animals[owner['id']]:
            if animal.name.split(' ')[-1] == animal_name:
                self.owned_animals[owner['id']].remove(animal)
                return animal
        return None

    def random_available_animal(self):
        return random.choice(list(self.available_animals.values()))

    def random_owned(self, owner):
        return random.choice(self.owned_animals[owner['id']])

    def send_message(self, recipient, message_text, sender=None):
        sender = sender or self.genie
        rctogether.send_message(
            sender.id, f"@**{recipient['person_name']}** {message_text}"
        )

    def handle_mention(self, adopter, message):
        print(message)
        m = re.search(
            r"adopt (a|an|the|one)? ([A-Za-z-]+),? please",
            message["text"],
            re.IGNORECASE,
        )
        if m:
            animal_name = m.groups()[1]
            if animal_name == "horse":
                self.send_message(adopter, "Sorry, that's just a picture of a horse.")
                return

            if animal_name == "genie":
                self.send_message(adopter, "You can't adopt me. I'm not a pet!")
                return

            animal = self.get_by_name(animal_name)
            print(animal)

            if not animal:
                alternative = self.random_available_animal().name
                self.send_message(
                    adopter,
                    f"Sorry, we don't have {a_an(animal_name)} at the moment, perhaps you'd like {a_an(alternative)} instead?",
                )
                return

            self.send_message(
                adopter,
                NOISES.get(animal.emoji, '💖'),
                animal,
            )
            rctogether.update_bot(
                animal.id, {"name": f"{adopter['person_name']}'s {animal.name}"}
            )
            del self.available_animals[position_tuple(animal.bot_json["pos"])]
            #  self.available_animals[position_tuple(animal.bot_json["pos"])] = self.spawn_animal(animal['pos'])
            self.owned_animals[adopter["id"]].append(animal)

            print("owned_animals: ", self.owned_animals)

            return


        m = re.search(
            r"adopt (a|an|the|one)? ([A-Za-z-]+)", message["text"], re.IGNORECASE
        )
        if m:
            self.send_message(
                adopter, "No please? Our pets are only available to polite homes."
            )
            return

        m = re.search("thank", message["text"], re.IGNORECASE)
        if m:
            self.send_message(
                adopter, random.choice(["You're welcome!", "No problem!", "❤️"])
            )
            return

        m = re.search("time to restock", message["text"], re.IGNORECASE)
        if m:
            self.restock_inventory()
            self.send_message(adopter, "New pets now in stock!")
            return

        m = re.search(r"abandon my ([A-Za-z-]+)", message["text"], re.IGNORECASE)
        if m:
            animal_name = m.groups()[0]
            animal = self.pop_owned_by_type(animal_name, adopter)
            if animal:
                self.send_message(adopter, sad_message(animal_name), animal)
                rctogether.delete_bot(animal.id)
            else:
                self.send_message(adopter, f"Sorry, you don't have a {animal_name}. Would you like to abandon your {self.random_owned(adopter).name.split(' ')[-1]} instead?")
            return


        self.send_message(
            adopter, "Sorry, I don't understand. Would you like to adopt a pet?"
        )

    def handle_entity(self, entity):
        if entity["type"] == "Avatar":
            message = entity.get("message")

            if message and self.genie.id in message["mentioned_entity_ids"]:
                message_dt = datetime.datetime.strptime(
                    message["sent_at"], "%Y-%m-%dT%H:%M:%SZ"
                )
                if message_dt <= self.processed_message_dt:
                    print("Skipping old message: ", message)
                else:
                    self.handle_mention(entity, message)
                    self.processed_message_dt = message_dt

        if entity["type"] == "Avatar":
            for animal in self.owned_animals.get(entity["id"], []):
                print(entity)
                position = offset_position(entity["pos"], random.choice(DELTAS))
                print(f"Moving {animal} to {position}")
                animal.update(position)


DELTAS = [{"x": x, "y": y} for x in [-1, 0, 1] for y in [-1, 0, 1] if x != 0 or y != 0]


def offset_position(position, delta):
    return {"x": position["x"] + delta["x"], "y": position["y"] + delta["y"]}


agency = Agency()
subscription = rctogether.RcTogether(callbacks=[agency.handle_entity])
subscription.block_until_done()
