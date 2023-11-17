import asyncio
import pytest
from pets.update_queues import UpdateQueues, deduplicated_updates
import pets.update_queues

pets.update_queues.SLEEP_AFTER_UPDATE = 0.01


@pytest.mark.asyncio
async def test_task_order_preservation():
    update_queues = UpdateQueues(deduplicated_updates)

    results = []

    async def mock_task(number):
        results.append(number)
        return number

    queue_id = "test_queue"
    task_ids = [1, 2, 3]
    for number in task_ids:
        await update_queues.add_task(queue_id, mock_task(number))
        await asyncio.sleep(0.10)

    await update_queues.close()

    assert results == task_ids, "Tasks are not processed in the order they were added"


@pytest.mark.asyncio
async def test_task_deduplication():
    update_queues = UpdateQueues(deduplicated_updates)

    tasks_processed = []

    async def mock_task(task_id):
        await asyncio.sleep(0.1)
        tasks_processed.append(task_id)

    queue_id = "test_queue"

    for task_id in range(9):
        await update_queues.add_task(queue_id, mock_task(task_id))
    await update_queues.close()

    assert len(tasks_processed) == 1


@pytest.mark.asyncio
async def test_queued_tasks_deduplication():
    queue = asyncio.Queue()

    updates = ["update1", "update2", "update3"]
    for update in updates:
        await queue.put(update)

    await queue.put(None)

    yielded_updates = []
    async for update in deduplicated_updates(queue):
        yielded_updates.append(update)

    assert yielded_updates == ["update3"]


@pytest.mark.asyncio
async def test_queued_tasks_sequencing():
    queue = asyncio.Queue()

    tasks = deduplicated_updates(queue)

    await queue.put("update1")
    assert await tasks.__anext__() == "update1"

    await queue.put("update2")
    assert await tasks.__anext__() == "update2"
