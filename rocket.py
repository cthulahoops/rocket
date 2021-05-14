import eventlet

eventlet.monkey_patch()

import time
import logging
import traceback
import random

import rctogether

logging.basicConfig(level=logging.INFO)

# Launch station. (Where the rocket start.)
# Control computer. (Note block check for name.)
# Collision detection.



CONTROL_COMPUTER = {"x": 27, "y": 61}
LAUNCH_PAD = {"x": 25, "y": 60}

TARGETS = {}
ROCKET_LOCATION = None

def normalise_name(name):
    if name is None:
        return None
    return name.strip("\n\r\t \u200b")

def first_name(s):
    return s.split(" ")[0]

def debris_message(emoji, target, instigator):
    return PAYLOADS[emoji] % {
        "victim": first_name(target),
        "instigator": first_name(instigator),
    }


PAYLOADS = {
    "💥": "%(victim)s was exploded by %(instigator)s",
    "🎉": "%(victim)s was aggressively thanked by %(instigator)s",
    "🐄": "COW!!!!!",
    "🔥": "%(victim)s is on fire",
    "💧": "WATER FIGHT!",
    "🌈": "%(victim)s got their groove back!",
    "💕": "%(victim)s was valentined by a secret admirer",
    "🦆": "Look at %(instigator)s's duck! QUACK! QUACK!",
    "🍅": "%(victim)s was booed off stage by %(instigator)s",
    "🥉": "%(victim)s was THIRD PLACED by %(instigator)s",
}


class Bot:
    def __init__(self, name, emoji, x, y):
        self.bot_json = rctogether.create_bot(name=name, emoji=emoji, x=x, y=y)
        self.queue = eventlet.Queue()
        eventlet.spawn(self.run)

    @property
    def id(self):
        return self.bot_json["id"]

    def run(self):
        while True:
            update = self.queue.get()
            while not self.queue.empty():
                print("Skipping outdated update: ", update)
                update = self.queue.get()
            print("Applying update: ", update)
            eventlet.sleep(1)
            rctogether.update_bot(self.bot_json["id"], update)

    def update(self, update):
        self.queue.put(update)

    def update_data(self, data):
        self.bot_json = data


class ClankyBotLauchSystem:
    def __init__(self):
        self.instigator = None
        self.target = "Nobody"
        self.rocket = Bot(name="Rocket Bot", emoji="🚀", x=LAUNCH_PAD["x"], y=LAUNCH_PAD["y"])
        self.gc_bot = GarbageCollectionBot()

    def respawn_rocket(self):
        self.instigator = None
        self.rocket = Bot(name="Rocket Bot", emoji="🚀", x=LAUNCH_PAD["x"], y=LAUNCH_PAD["y"])
        self.target = "Nobody"

    def handle_instruction(self, entity):
        print("New instructions received: ", entity)
        note_text = entity.get("note_text")
        if note_text == "":
            self.instigator = None
            self.target = "Nobody"
            self.rocket.update(LAUNCH_PAD)
        else:
            self.instigator = entity.get("updated_by").get("name")
            self.target = normalise_name(note_text)
            if self.target in TARGETS:
                self.rocket.update(TARGETS[self.target])

    def handle_rocket_move(self, entity):
        self.rocket.update_data(entity)
        rocket_position = entity["pos"]
        target_position = TARGETS.get(self.target)

        print("TARGET HIT: ", rocket_position, target_position)
        if rocket_position == target_position:
            emoji = random.choice(list(PAYLOADS))
            self.rocket.update(
                {
                    "emoji": emoji,
                    "name": debris_message(emoji, self.target, self.instigator)
                }
            )
            self.gc_bot.add_garbage(self.rocket.bot_json)
            self.respawn_rocket()

    def handle_target_detected(self, entity):
        target_position = entity["pos"]
        print("Target detected at: ", target_position)
        self.rocket.update(target_position)


    def handle_entity(self, entity):
        person_name = normalise_name(entity.get("person_name"))
        if person_name:
            TARGETS[person_name] = entity["pos"]

        if entity.get("app") and entity["app"]["name"] == "rocket":
            print("App entity update: ", entity)

        if person_name == self.target:
            self.handle_target_detected(entity)

        elif entity.get("pos") == {"x": 27, "y": 61}:
            self.handle_instruction(entity)

        elif entity["id"] == self.rocket.id:
            self.handle_rocket_move(entity)

        elif entity["id"] == self.gc_bot.id:
            self.gc_bot.handle_update(entity)

class GarbageCollectionBot:
    def __init__(self):
        self.garbage_bot = Bot(name="Garbage Collector", emoji="🛺", x=22, y=61)
        self.garbage_queue = eventlet.Queue()
        self.garbage = None

        eventlet.spawn(self.run)

    def run(self):
        while True:
            if self.garbage_queue.qsize() <= 3:
                print("Not enough garbage, let's just rest a bit!")
                eventlet.sleep(60)
            elif self.garbage:
                print("Hey, we're already busy here.")
                eventlet.sleep(60)
            else:
                self.collect(self.garbage_queue.get())

    @property
    def id(self):
        return self.garbage_bot.id

    def add_garbage(self, garbage):
        self.garbage_queue.put(garbage)

    def collect(self, garbage):
        self.garbage = garbage
        print("Crew dispatched to collect: ", self.garbage)
        self.garbage_bot.update(self.garbage["pos"])

    def complete_collection(self):
        eventlet.sleep(15)
        print("Ready to complete collection!")
        rctogether.delete_bot(self.garbage["id"])
        self.garbage = None
        self.garbage_bot.update({"x": 22, "y": 61})

    def handle_update(self, entity):
        if self.garbage and entity["pos"] == self.garbage["pos"]:
            print("Collection complete: ", entity, self.garbage)
            eventlet.spawn(self.complete_collection)

def main():
    try:
        rctogether.clean_up_bots()

        launch_system = ClankyBotLauchSystem()

        subscription = rctogether.RcTogether(callbacks=[launch_system.handle_entity])
        subscription.block_until_done()
    finally:
        print("Exitting... cleaning up.")
        rctogether.clean_up_bots()

if __name__ == '__main__':
    main()
