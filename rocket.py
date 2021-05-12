import logging
import traceback
import random

import rctogether

logging.basicConfig(level=logging.INFO)

# Launch station. (Where the rocket start.)
# Control computer. (Note block check for name.)
# Collision detection.

# Clean up existing bots.
for bot in rctogether.get_bots():
    rctogether.delete_bot(bot["id"])

CONTROL_COMPUTER = {'x': 27, 'y': 61}
LAUNCH_PAD = {'x': 25, 'y': 60}
TARGET = "Nobody"

TARGETS = {}
ROCKET_LOCATION = None

PAYLOADS = ['💥', '🎊', '🐄', '🔥', '💧', '🌈']

class ClankyBotLauchSystem:
    def __init__(self):
        self.target = "Nobody"
        self.rocket = self._new_rocket()

    def respawn_rocket(self):
        self.rocket = self._new_rocket()
        self.target = "Nobody"

    def _new_rocket(self):
        return rctogether.create_bot(name="Rocket Bot", emoji="🚀", x=LAUNCH_PAD['x'], y=LAUNCH_PAD['y'])

LAUNCH_SYSTEM = ClankyBotLauchSystem()

def handle_entity(entity):
    person_name = entity.get("person_name")
    if person_name:
        TARGETS[person_name] = entity["pos"]

    if person_name == LAUNCH_SYSTEM.target:
        target_position = entity["pos"]
        print("Target detected at: ", LAUNCH_SYSTEM.rocket, target_position)
        rctogether.update_bot(LAUNCH_SYSTEM.rocket["id"], target_position)
    elif entity.get("pos") == {'x': 27, 'y': 61}:
        note_text = entity.get("note_text")
        if note_text == '':
            LAUNCH_SYSTEM.target = "Nobody"
            rctogether.update_bot(LAUNCH_SYSTEM.rocket["id"], LAUNCH_PAD)
        else:
            LAUNCH_SYSTEM.target = note_text
            if LAUNCH_SYSTEM.target in TARGETS:
                rctogether.update_bot(LAUNCH_SYSTEM.rocket["id"], TARGETS[LAUNCH_SYSTEM.target])
    elif entity['id'] == LAUNCH_SYSTEM.rocket["id"]:
        rocket_position = entity['pos']
        target_position = TARGETS.get(LAUNCH_SYSTEM.target)

        print(rocket_position, target_position)
        if rocket_position == target_position:
            rctogether.update_bot(LAUNCH_SYSTEM.rocket["id"], {'emoji': random.choice(PAYLOADS)})
            LAUNCH_SYSTEM.respawn_rocket()

def handle_message(message):
    try:
        if message["type"] == "world":
            for entity in message["payload"]["entities"]:
                handle_entity(entity)
        else:
            handle_entity(message["payload"])
    except Exception as exc:
        traceback.print_exc()
        raise


subscription = rctogether.subscribe(on_receive=handle_message)
rctogether.block_until_done(subscription)
