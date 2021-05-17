import rctogether

destinations = [{'x': 20, 'y': 50}, {'x': 20, 'y': 80}, {'x': 1, 'y': 80}, {'x': 1, 'y': 50}]

def visit_destination(update):
    print(update)
    if update['pos'] in destinations:
        next_pos = destinations[(destinations.index(update['pos']) + 1) % len(destinations)]
        octopus.update(next_pos)

subscription = rctogether.RcTogether()
octopus = subscription.create_bot(name="Test Octopus", emoji="🐙", x=1, y=50, handle_update=visit_destination)
subscription.block_until_done()
