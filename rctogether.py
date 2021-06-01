import os
import time
import traceback
import eventlet

import requests
from actioncable.connection import Connection
from actioncable.subscription import Subscription

RC_APP_ID = os.environ["RC_APP_ID"]
RC_APP_SECRET = os.environ["RC_APP_SECRET"]
RC_APP_ENDPOINT = os.environ.get("RC_ENDPOINT", "recurse.rctogether.com")

class HttpError(Exception):
    pass

def api_url(resource, resource_id=None):
    if resource_id is not None:
        resource = f"{resource}/{resource_id}"

    return f"https://{RC_APP_ENDPOINT}/api/{resource}?app_id={RC_APP_ID}&app_secret={RC_APP_SECRET}"


def parse_response(response):
    if response.status_code != 200:
        raise HttpError(response.status_code, response.text)
    return response.json()


def get_bots():
    r = requests.get(url=api_url("bots"))
    return parse_response(r)


def delete_bot(bot_id):
    r = requests.delete(url=api_url("bots", bot_id))
    return parse_response(r)


def create_bot(name, emoji, x=5, y=2, direction="right", can_be_mentioned=False):
    r = requests.post(
        url=api_url("bots"),
        json={
            "bot": {
                "name": name,
                "emoji": emoji,
                "x": x,
                "y": y,
                "direction": direction,
                "can_be_mentioned": can_be_mentioned,
            }
        },
    )
    return parse_response(r)


def update_bot(bot_id, bot_attributes):
    r = requests.patch(url=api_url("bots", bot_id), json={"bot": bot_attributes})
    return parse_response(r)

def send_message(bot_id, message_text):
    r = requests.post(
            url=api_url("messages"),
            json={"bot_id": bot_id, "text": message_text}
    )
    return parse_response(r)

def clean_up_bots():
    for bot in get_bots():
        delete_bot(bot["id"])

def with_tracebacks(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise
    return wrapper

class Bot:
    def __init__(self, json, handle_update=None):
        self.bot_json = json
        self.queue = eventlet.Queue()
        self.handle_update = handle_update
        eventlet.spawn(self.run)

    @classmethod
    def create(cls, name, emoji, x, y, handle_update=None, can_be_mentioned=False):
        json = create_bot(name=name, emoji=emoji, x=x, y=y, can_be_mentioned=can_be_mentioned)
        return cls(json, handle_update)

    @property
    def id(self):
        return self.bot_json["id"]

    @property
    def emoji(self):
        return self.bot_json["emoji"]

    @property
    def name(self):
        return self.bot_json["name"]

    def run(self):
        while True:
            update = self.queue.get()
            while not self.queue.empty():
                print("Skipping outdated update: ", update)
                update = self.queue.get()
            print("Applying update: ", update)
            try:
                update_bot(self.id, update)
            except HttpError as exc:
                print(f"Update failed: {self!r}, {exc!r}")
            eventlet.sleep(1)

    def update(self, update):
        self.queue.put(update)

    def update_data(self, data):
        self.bot_json = data

    def handle_entity(self, entity):
        print("Bot update!")
        self.bot_json = entity
        if self.handle_update:
            self.handle_update(entity)

    def __repr__(self):
        return "<Bot name=%r>" % (self.name,)


class RcTogether:
    def __init__(self, callbacks=[]):
        self.connection = Connection(
            origin=f"https://{RC_APP_ENDPOINT}",
            url=f"wss://{RC_APP_ENDPOINT}/cable?app_id={RC_APP_ID}&app_secret={RC_APP_SECRET}",
        )
        self.connection.connect()

        while not self.connection.connected:
            # TODO - use callbacks to detect connection!
            print("Waiting for connection.")
            time.sleep(0.1)
        print("Connected.")


        self.subscription = Subscription(self.connection, identifier={"channel": "ApiChannel"})
        # Websocket library captures and hides tracebacks, so make sruer
        self.subscription.on_receive(with_tracebacks(self.handle_message))
        self.subscription.create()

        self.callbacks = callbacks
        self.bots = {}

    def block_until_done(self):
        self.connection.ws_thread.join()

    def create_bot(self, name, emoji, x, y, handle_update, can_be_mentioned=False):
        bot = Bot.create(name, emoji, x, y, handle_update, can_be_mentioned)
        self.bots[bot.id] = bot
        return bot

    def handle_message(self, message):
        if message["type"] == "world":
            for entity in message["payload"]["entities"]:
                self.handle_entity(entity)
        else:
            self.handle_entity(message["payload"])

    def handle_entity(self, entity):
        for callback in self.callbacks:
            callback(entity)

        if entity['id'] in self.bots:
            self.bots[entity['id']].handle_entity(entity)

    def add_callback(self, callback):
        self.callbacks.append(callback)
