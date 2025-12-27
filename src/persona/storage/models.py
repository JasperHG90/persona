from pydantic import BaseModel

from persona.types import personaTypes


class IndexEntry(BaseModel):
    name: str | None = None
    description: str | None = None
    uuid: str | None = None
    files: list[str] | None = None
    embedding: list[float] | None = None
    type: personaTypes | None = None

    def update(self, key: str, value: list[float] | list[str] | str | None):
        setattr(self, key, value)
