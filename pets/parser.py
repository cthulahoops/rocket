import re
from typing import Optional, Tuple, Match
from .constants import MANNER_PREFIXES

COMMANDS = {
    "time to restock": "restock",
    r"(?:look after|take care of|drop off) my ([A-Za-z]+)": "day_care_drop_off",
    r"(?:collect|pick up|get) my ([A-Za-z]+)": "day_care_pick_up",
    "thank": "thanks",
    r"abandon my ([A-Za-z-]+)": "abandon",
    r"well[- ]actually|feigning surprise|backseat driving|subtle[- ]*ism": "social_rules",
    r"pet the ([A-Za-z-]+)": "pet_a_pet",
    r"give my ([A-Za-z]+) to": "give_pet",
    r"help": "help",
}


def parse_adoption(message: str) -> Optional[Match]:
    """Special parser for adoption commands that handles 'pet' ambiguity."""
    pet_match = re.search(
        r"(.*adopt (?:a|an|the|one)? ([A-Za-z'-]+)\s*([A-Za-z'-]*).*)",
        message,
        re.IGNORECASE,
    )

    if not pet_match:
        return None

    first_word = pet_match.group(2).lower() if pet_match.group(2) else ""
    second_word = pet_match.group(3).lower() if pet_match.group(3) else ""

    if first_word == "pet":
        if second_word and second_word not in MANNER_PREFIXES:
            return (pet_match.group(0), second_word)
        return (pet_match.group(0), "pet")

    return (pet_match.group(0), first_word)


def parse_command(message: str) -> Optional[Tuple[str, Match]]:
    # Special handling for adoption commands
    adoption_match = parse_adoption(message)
    if adoption_match:
        return "adoption", Groups(adoption_match)

    # Regular command parsing
    for pattern, command in COMMANDS.items():
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return command, match
    return None


class Groups:
    def __init__(self, args):
        self.args = args

    def groups(self):
        return self.args
