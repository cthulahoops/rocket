import logging

import rctogether

logging.basicConfig(level=logging.INFO)

# Launch station. (Where the rocket start.)
# Control computer. (Note block check for name.)
# Collision detection.

CONTROL_COMPUTER = {'x': 27, 'y': 61}
LAUNCH_PAD = {'x': 25, 'y': 60}
TARGET = "Nobody"

TARGETS = {}


def handle_entity(entity):
    global TARGET

    person_name = entity.get("person_name")
    if person_name:
        TARGETS[person_name] = entity["pos"]

    if entity.get("person_name") == TARGET:
        target_position = entity["pos"]
        print("Target detected at: ", target_position)
        rctogether.update_bot(rocket["id"], target_position)
    elif entity.get("pos") == {'x': 27, 'y': 61}:
        # {'type': 'entity', 'payload': {'id': 77522, 'type': 'Note', 'pos': {'x': 27, 'y': 61}, 'color': 'gray', 'note_text': '"Adam Kelly"', 'updated_by': {'name': 'Hannah Wolff', 'id': 46465}, 'note_updated_at': '2021-05-12T12:43:57Z'}}
        print(entity)
        note_text = entity.get("note_text")
        if note_text == '':
            TARGET = "Nobody"
            rctogether.update_bot(rocket["id"], LAUNCH_PAD)
        else:
            TARGET = note_text
            if TARGET in TARGETS:
                rctogether.update_bot(rocket["id"], TARGETS[TARGET])

def handle_message(message):
    if message["type"] == "world":
        for entity in message["payload"]["entities"]:
            handle_entity(entity)
    else:
        handle_entity(message["payload"])

subscription = rctogether.subscribe(on_receive=handle_message)

# Clean up existing bots.
for bot in rctogether.get_bots():
    rctogether.delete_bot(bot["id"])

rocket = rctogether.create_bot(name="Rocket Bot", emoji="🚀", x=LAUNCH_PAD['x'], y=LAUNCH_PAD['y'])

rctogether.block_until_done(subscription)
