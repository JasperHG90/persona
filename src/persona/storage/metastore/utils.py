from typing import Any, Literal, Protocol


class CursorLike(Protocol):
    def rollback(self) -> Any:
        ...
        
    def commit(self) -> Any:
        ...
        
    def begin(self) -> Any:
        ...
        
    def close(self) -> Any:
        ...
        
    def execute(self, query: str, parameters: list | None = None) -> Any:
        ...


personaTypes = Literal['roles', 'skills']
