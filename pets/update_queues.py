import asyncio
import rctogether

SLEEP_AFTER_UPDATE = 0.001


class UpdateQueues:
    def __init__(self, queue_iterator):
        self.queues = {}
        self.tasks = {}
        self.queue_iterator = queue_iterator

    async def add_task(self, queue_id, task):
        if queue_id not in self.queues:
            queue = asyncio.Queue()
            self.queues[queue_id] = queue
            self.tasks[queue_id] = asyncio.create_task(self.run(queue_id, queue))

        await self.queues[queue_id].put(task)

    async def run(self, queue_id, queue):
        async for task in self.queue_iterator(queue, queue_id):
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


async def get_all_available_updates(queue):
    updates = []
    updates.append(await queue.get())

    while not queue.empty():
        update = await queue.get()
        updates.append(update)
        if update is None:
            break

    return updates


async def deduplicated_updates(queue, queue_id=None):
    while True:
        updates = await get_all_available_updates(queue)

        print("Updates: ", updates)

        if updates[-1] is None:
            while updates and updates[-1] is None:
                updates.pop()

            if updates:
                yield updates[-1]
            return

        yield updates[-1]
