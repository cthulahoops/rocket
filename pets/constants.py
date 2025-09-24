"""Shared constants for the pets module."""

MANNERS = [
    "please",
    "bitte",
    "le do thoil",
    "sudo",
    "per favore",
    "oh mighty djinn",
    "s'il vous plaît",
    "s'il vous plait",
    "svp",
    "por favor",
    "kudasai",
    "onegai shimasu",
    "пожалуйста",
]

PETS = [
    {"emoji": "🦇", "name": "bat", "noise": "screech!"},
    {"emoji": "🐻", "name": "bear", "noise": "ROAR!"},
    {"emoji": "🐝", "name": "bee", "noise": "buzz!"},
    {"emoji": "🦕", "name": "brontosaurus", "noise": "MEEEHHH!"},
    {"emoji": "🐫", "name": "camel"},
    {"emoji": "🐈", "name": "cat", "noise": "miaow!"},
    {"emoji": "🐛", "name": "caterpillar", "noise": "munch!"},
    {"emoji": "🐄", "name": "cow", "noise": "Moo!"},
    {"emoji": "🦀", "name": "crab", "noise": "click!"},
    {"emoji": "🐊", "name": "crocodile"},
    {"emoji": "🐕", "name": "dog", "noise": "woof!"},
    {"emoji": "🐉", "name": "dragon", "noise": "🔥"},
    {"emoji": "🦅", "name": "eagle"},
    {"emoji": "🐘", "name": "elephant"},
    {"emoji": "🦩", "name": "flamingo"},
    {"emoji": "🦊", "name": "fox", "noise": "Wrahh!"},
    {"emoji": "🐸", "name": "frog", "noise": "ribbet!"},
    {"emoji": "🦒", "name": "giraffe"},
    {"emoji": "🦔", "name": "hedgehog", "noise": "scurry, scurry, scurry"},
    {"emoji": "🦛", "name": "hippo"},
    {"emoji": "👾", "name": "invader"},
    {"emoji": "🦘", "name": "kangaroo", "noise": "Chortle chortle!"},
    {"emoji": "🐨", "name": "koala", "noise": "gggrrrooowwwlll"},
    {"emoji": "🦙", "name": "llama"},
    {"emoji": "🐁", "name": "mouse", "noise": "squeak!"},
    {"emoji": "🦉", "name": "owl", "noise": "hoot hoot!"},
    {"emoji": "🦜", "name": "parrot", "noise": "HELLO!"},
    {"emoji": "🐧", "name": "penguin"},
    {"emoji": "🐖", "name": "pig", "noise": "oink!"},
    {"emoji": "🐇", "name": "rabbit"},
    {"emoji": "🚀", "name": "rocket"},
    {"emoji": "🐌", "name": "snail", "noise": "slurp!"},
    {"emoji": "🦖", "name": "t-rex", "noise": "RAWR!"},
    {"emoji": "🐅", "name": "tiger"},
    {"emoji": "🐢", "name": "turtle", "noise": "hiss!"},
    {"emoji": "🦄", "name": "unicorn", "noise": "✨"},
    {"emoji": "🪨", "name": "rock", "noise": "🤘"},
]

# Derived constants
ANIMAL_NAMES = {pet["name"].lower() for pet in PETS}
MANNER_WORDS = {manner.lower() for manner in MANNERS}

