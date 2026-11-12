from dataclasses import dataclass, field
from typing import Annotated, List, Optional
from timefold.solver.domain import (
    planning_entity,
    planning_solution,
    PlanningId,
    PlanningVariable,
    PlanningPin,
    PlanningScore,
    ProblemFactCollectionProperty,
    PlanningEntityCollectionProperty,
    ValueRangeProvider,
)
from timefold.solver.score import HardSoftScore

from app.domain.enums import WeekFrequency
from app.domain.models import BaseSlot, Room, Teacher, AtomicGroup, ExternalBlock


@planning_entity
@dataclass
class Lesson:
    id: Annotated[str, PlanningId]
    subject: str
    teacher_id: str
    atomic_group_ids: List[str]  # Список ID атомарных подгрупп
    student_count: int
    frequency: WeekFrequency
    required_features: List[str] = field(default_factory=list)
    pinned: Annotated[bool, PlanningPin] = False

    # Planning variables
    timeslot: Annotated[
        Optional[BaseSlot],
        PlanningVariable(value_range_provider_refs=["timeslot_range"]),
    ] = None
    room: Annotated[
        Optional[Room],
        PlanningVariable(value_range_provider_refs=["room_range"]),
    ] = None

    def __bool__(self) -> bool:
        return True

    def __repr__(self) -> str:
        pin_str = "[PIN]" if self.pinned else ""
        slot_str = self.timeslot.id if self.timeslot else "None"
        room_str = self.room.name if self.room else "None"
        return f"Lesson({pin_str}{self.id}:{self.subject} @ {slot_str} in {room_str}, freq={self.frequency.value})"


@planning_solution
@dataclass
class TimetableSolution:
    id: Annotated[str, PlanningId]
    timeslots: Annotated[
        List[BaseSlot],
        ProblemFactCollectionProperty,
        ValueRangeProvider(id="timeslot_range"),
    ]
    rooms: Annotated[
        List[Room],
        ProblemFactCollectionProperty,
        ValueRangeProvider(id="room_range"),
    ]
    teachers: Annotated[
        List[Teacher],
        ProblemFactCollectionProperty,
    ]
    atomic_groups: Annotated[
        List[AtomicGroup],
        ProblemFactCollectionProperty,
    ]
    external_blocks: Annotated[
        List[ExternalBlock],
        ProblemFactCollectionProperty,
    ]
    lessons: Annotated[
        List[Lesson],
        PlanningEntityCollectionProperty,
    ]
    score: Annotated[
        Optional[HardSoftScore],
        PlanningScore,
    ] = None
