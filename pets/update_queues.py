import asyncio
import rctogether

SLEEP_AFTER_UPDATE = 0.01


class UpdateQueues:
    def __init__(self):
        self.queues = {}
        self.tasks = {}

    async def add_task(self, queue_id, task):
        if queue_id not in self.queues:
            queue = asyncio.Queue()
            self.queues[queue_id] = queue
            self.tasks[queue_id] = asyncio.create_task(self.run(queue_id, queue))

        await self.queues[queue_id].put(task)

    async def run(self, queue_id, queue):
        async for task in queued_tasks(queue):
            try:
                await task
            except rctogether.api.HttpError as exc:
                print(f"Update failed: {queue_id!r}, {exc!r}")

            await asyncio.sleep(SLEEP_AFTER_UPDATE)

    async def close(self):
        for queue in self.queues.values():
            await queue.put(None)

        for task in self.tasks.values():
            await task


async def queued_tasks(queue):
    while True:
        update = await queue.get()

        while update is not None and not queue.empty():
            next_update = await queue.get()
            if next_update is None:
                yield update
            update = next_update

        if update is None:
            return

        yield update
