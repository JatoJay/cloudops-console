import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID


class ProgressBroker:
    """Fan out in-process analysis progress and replay it to late subscribers."""

    def __init__(self) -> None:
        self._history: dict[UUID, list[str]] = defaultdict(list)
        self._subscribers: dict[UUID, set[asyncio.Queue[str]]] = defaultdict(set)

    async def publish(self, analysis_id: UUID, message: str) -> None:
        self._history[analysis_id].append(message)
        for queue in tuple(self._subscribers.get(analysis_id, ())):
            await queue.put(message)

    @asynccontextmanager
    async def subscribe(self, analysis_id: UUID) -> AsyncIterator[asyncio.Queue[str]]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        for message in self._history.get(analysis_id, ()):
            queue.put_nowait(message)
        self._subscribers[analysis_id].add(queue)
        try:
            yield queue
        finally:
            self._subscribers[analysis_id].discard(queue)
            if not self._subscribers[analysis_id]:
                self._subscribers.pop(analysis_id, None)


progress_broker = ProgressBroker()
