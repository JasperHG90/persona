from pydantic import BaseModel


class IndexEntry(BaseModel):
    name: str | None = None
    description: str | None = None
    uuid: str | None = None

    def update(self, key: str, value: str | None):
        setattr(self, key, value)
