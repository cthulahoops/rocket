import os
import random
import threading
import requests

RC_APP_ID = os.environ["RC_APP_ID"]
RC_APP_SECRET = os.environ["RC_APP_SECRET"]
RC_APP_ENDPOINT = os.environ.get("RC_ENDPOINT", "recurse.rctogether.com")

def api_url(resource, resource_id=None):
    if resource_id is not None:
        resource = f"{resource}/{resource_id}"

    return f"https://{RC_APP_ENDPOINT}/api/{resource}?app_id={RC_APP_ID}&app_secret={RC_APP_SECRET}"

def create_snake():
    x = random.randint(142, 175)
    y = random.randint(1, 40)

    print("Creating at: ", x, y)
    response = requests.post(
        url=api_url("bots"),
        json={
            "bot": {
                "name": "OSsss Threadssssss!!!",
                "emoji": "🐍",
                "x": x,
                "y": y,
                "direction": "right",
                "can_be_mentioned": False,
            }
        },
    )
    print(response.json())

def main():
    threads = []
    for _ in range(10):
        t = threading.Thread(target=create_snake)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


if __name__ == '__main__':
    main()
