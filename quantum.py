import random
import asyncio
import arctogether

TARGET = {"x": 160, "y": 3}
PARTICLE_HOME = {"x": 160, "y": 10}
PARTICLE_AWAY = {"x": 160, "y": 28}


class RealityLab:
    def __init__(self):
        self.particle = None
        self.rc = None
        self.target_id = None

    async def handle_entity(self, entity):
        if entity["pos"] == {"x": 158, "y": 3} and entity.get("person_name") == "Adam Kelly":
            print("Initialise sequence!")
            asyncio.create_task(self.run_sequence())

        if entity["pos"] == TARGET:
            print("TARGET ACQUIRED: ", entity)
            if self.particle:
                await self.particle.update(TARGET)
                self.target_id = entity["id"]
        elif entity["id"] == self.target_id and entity["pos"] != TARGET:
            print("Target gone - reset.")
            await self.particle.update(PARTICLE_HOME)
            self.target_id = None

    async def handle_particle_move(self, entity):
        print("Particle move: ", entity, self.target_id, TARGET)

        if self.target_id:
            return

        if entity["pos"] == PARTICLE_HOME:
            await self.particle.update(PARTICLE_AWAY)
        else:
            await self.particle.update(PARTICLE_HOME)

    async def break_reality(self, pos):
        await asyncio.sleep(random.random() * 3)
        bot = await self.rc.create_bot(
            name="".join(random.choice("QJKXBqjkxb!^") for _ in range(8)),
            emoji=random.choice("⚡🔥💥"),
            x=pos["x"],
            y=pos["y"],
            handle_update=None,
        )
        await asyncio.sleep(random.random() * 2)
        await arctogether.update_bot(bot.id, {"emoji": random.choice("⚡🔥💥")})
        await asyncio.sleep(random.random() * 2)
        await arctogether.update_bot(bot.id, {"emoji": "🐞"})

    async def run_sequence(self):
        locations = [{"x": random.randint(152, 169), "y": random.randint(8, 27)} for _ in range(20)]
        asyncio.gather(*[self.break_reality(pos) for pos in locations])

    async def start(self):
        await arctogether.clean_up_bots()

        self.rc = arctogether.RcTogether(callbacks=[self.handle_entity])

        self.particle = await self.rc.create_bot(
            name="Particle",
            emoji="🔥",
            x=PARTICLE_HOME["x"],
            y=PARTICLE_HOME["y"],
            handle_update=self.handle_particle_move,
        )

        await self.rc.run_websocket()


if __name__ == "__main__":
    asyncio.run(RealityLab().start())
