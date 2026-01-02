from aenum import Enum
from typing import Literal

personaTypes = Literal['roles', 'skills']


class PersonaTypeEnum(Enum):  # type: ignore
    ROLES = 'roles'
    SKILLS = 'skills'


def fn(x: PersonaTypeEnum) -> str:
    return x.value
