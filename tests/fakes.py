from __future__ import annotations

from typing import Any


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]):
        self._docs = docs

    def sort(self, *_args: Any, **_kwargs: Any) -> "FakeCursor":
        return self

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for doc in self._docs:
            yield doc


class FakeCollection:
    def __init__(self):
        self._docs: dict[str, dict[str, Any]] = {}

    async def insert_one(self, doc: dict[str, Any]) -> None:
        self._docs[doc["_id"]] = doc

    async def find_one(self, filter_: dict[str, Any]) -> dict[str, Any] | None:
        return self._docs.get(filter_.get("_id"))

    def find(self, filter_: dict[str, Any]) -> FakeCursor:
        if not filter_:
            docs = list(self._docs.values())
        else:
            docs = [d for d in self._docs.values() if all(d.get(k) == v for k, v in filter_.items())]
        return FakeCursor(docs)


class FakeDatabase:
    def __init__(self):
        self._collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self._collections.setdefault(name, FakeCollection())


class FakeMongoClient:
    def __init__(self):
        self._databases: dict[str, FakeDatabase] = {}

    def __getitem__(self, name: str) -> FakeDatabase:
        return self._databases.setdefault(name, FakeDatabase())

    async def close(self) -> None:
        pass
