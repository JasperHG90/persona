from pydantic import BaseModel, RootModel


class IndexEntry(BaseModel):
    name: str | None = None
    description: str | None = None
    uuid: str | None = None

    def update(self, key: str, value: str | None):
        setattr(self, key, value)


class SubIndex(RootModel[dict[str, IndexEntry]]):
    def exists(self, name: str) -> bool:
        return name in self.root.keys()

    def upsert(self, entry: IndexEntry):
        if not entry.name:
            raise ValueError('IndexEntry must have a name to be upserted.')
        self.root[entry.name] = entry

    def delete(self, name: str):
        self.root.pop(name, None)


class Index(BaseModel):
    personas: SubIndex
    skills: SubIndex
