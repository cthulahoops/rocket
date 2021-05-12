import logging

import rctogether

logging.basicConfig(level=logging.DEBUG)


def handle_message(message):
    if message["type"] == "world":
        pass
    elif message["payload"].get("person_name") == "Adam Kelly":
        target_position = message["payload"]["pos"]
        print("Target detected at: ", target_position)
        rctogether.update_bot(rocket["id"], target_position)
    else:
        print(message)


subscription = rctogether.subscribe(on_receive=handle_message)

# Clean up existing bots.
for bot in rctogether.get_bots():
    rctogether.delete_bot(bot["id"])

rocket = rctogether.create_bot(name="Rocket Bot", emoji="🚀", x=2, y=2)

rctogether.block_until_done(subscription)
