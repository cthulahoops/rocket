import os
import time

import requests
from actioncable.connection import Connection
from actioncable.subscription import Subscription

RC_APP_ID = os.environ["RC_APP_ID"]
RC_APP_SECRET = os.environ["RC_APP_SECRET"]
RC_APP_ENDPOINT = os.environ.get("RC_ENDPOINT", "recurse.rctogether.com")


def api_url(resource, resource_id=None):
    if resource_id is not None:
        resource = f"{resource}/{resource_id}"

    return f"https://{RC_APP_ENDPOINT}/api/{resource}?app_id={RC_APP_ID}&app_secret={RC_APP_SECRET}"


def parse_response(response):
    if response.status_code != 200:
        raise Exception(response.status_code, response.body)
    return response.json()


def get_bots():
    r = requests.get(url=api_url("bots"))
    return parse_response(r)


def delete_bot(bot_id):
    r = requests.delete(url=api_url("bots", bot_id))
    return parse_response(r)


def create_bot(name, emoji, x=5, y=2, direction="right", can_be_mentioned=True):
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


def subscribe(on_receive):
    connection = Connection(
        origin=f"https://{RC_APP_ENDPOINT}",
        url=f"wss://{RC_APP_ENDPOINT}/cable?app_id={RC_APP_ID}&app_secret={RC_APP_SECRET}",
    )
    connection.connect()

    while not connection.connected:
        # TODO - use callbacks to detect connection!
        time.sleep(0.1)

    subscription = Subscription(connection, identifier={"channel": "ApiChannel"})
    subscription.on_receive(on_receive)
    subscription.create()

    return {"connection": connection, "subscription": subscription}


def block_until_done(subscription):
    subscription["connection"].ws_thread.join()
