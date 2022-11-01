import asyncio
import rctogether
import pets

EMOJI = {pet['name']: pet['emoji'] for pet in pets.PETS}
EMOJI['sheep'] = "🐑"
EMOJI['duck'] = "🦆"

async def main():
    async with rctogether.RestApiSession() as session:
        bots = await rctogether.bots.get(session)
        for bot in bots:
            if bot['emoji'] == '🧞':
                continue
            pet_type = bot['name'].split(" ")[-1]
            original_emoji = EMOJI.get(pet_type)
            if not original_emoji:
                print("Original unavailable: ", bot)
            if original_emoji and original_emoji != bot['emoji']:
                print(bot)
                print(pet_type, bot['emoji'], original_emoji)
                await rctogether.bots.update(session, bot['id'], {'emoji': original_emoji})
                await asyncio.sleep(0.2)

if __name__ == "__main__":
    asyncio.run(main())
