from dataclasses import dataclass, field
from typing import Annotated, List, Set
from timefold.solver.domain import PlanningId

from app.domain.enums import DayOfWeek, WeekFrequency, TargetType


@dataclass(unsafe_hash=True)
class BaseSlot:
    id: Annotated[str, PlanningId]
    day_of_week: DayOfWeek
    slot_number: int  # 1..7

    def __bool__(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"Slot({self.id}:{self.day_of_week.value}_{self.slot_number})"


@dataclass(unsafe_hash=True)
class Room:
    id: Annotated[str, PlanningId]
    name: str
    capacity: int
    features: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return True

    def has_features(self, required: List[str]) -> bool:
        room_feats = set(self.features)
        return set(required).issubset(room_feats)

    def __repr__(self) -> str:
        return f"Room({self.id}:{self.name}, cap={self.capacity})"


@dataclass(unsafe_hash=True)
class Teacher:
    id: Annotated[str, PlanningId]
    name: str
    unavailable_slots: List[str] = field(default_factory=list)
    preferred_slots: List[str] = field(default_factory=list)
    unwanted_slots: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"Teacher({self.id}:{self.name})"


@dataclass(unsafe_hash=True)
class AtomicGroup:
    id: Annotated[str, PlanningId]
    name: str
    parent_group: str  # Имя родительской группы, напр. "ИС-21"
    student_count: int

    def __bool__(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"AtomicGroup({self.id}:{self.name}, count={self.student_count})"


@dataclass(unsafe_hash=True)
class ExternalBlock:
    id: Annotated[str, PlanningId]
    target_type: TargetType
    target_id: str  # teacher_id или atomic_group_id
    slot_id: str
    frequency: WeekFrequency
    reason: str = ""

    def __bool__(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"ExternalBlock({self.id}:{self.target_type.value}_{self.target_id}@{self.slot_id}_{self.frequency.value})"
