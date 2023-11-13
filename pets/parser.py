import re
from typing import Optional, Tuple, Match

COMMANDS = {
    "time to restock": "restock",
    "adopt (a|an|the|one)? ([A-Za-z-]+)": "adoption",
    r"(?:look after|take care of|drop off) my ([A-Za-z]+)": "day_care_drop_off",
    r"(?:collect|pick up|get) my ([A-Za-z]+)": "day_care_pick_up",
    "thank": "thanks",
    r"abandon my ([A-Za-z-]+)": "abandon",
    r"well[- ]actually|feigning surprise|backseat driving|subtle[- ]*ism": "social_rules",
    r"pet the ([A-Za-z-]+)": "pet_a_pet",
    r"give my ([A-Za-z]+) to": "give_pet",
    r"help": "help",
}


def parse_command(message: str) -> Optional[Tuple[str, Match]]:
    for pattern, command in COMMANDS.items():
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return command, match
    return None
