from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, model_validator

from app.domain.enums import DayOfWeek, WeekFrequency, TargetType


SLOT_BELLS: Dict[int, Tuple[str, str]] = {
    1: ("08:30", "10:00"),
    2: ("10:15", "11:45"),
    3: ("12:00", "13:30"),
    4: ("14:15", "15:45"),
    5: ("16:00", "17:30"),
    6: ("17:45", "19:15"),
    7: ("19:30", "21:00"),
}

TIME_SLOT_MAP: Dict[str, int] = {
    "08:30": 1,
    "8:30": 1,
    "10:15": 2,
    "12:00": 3,
    "14:15": 4,
    "16:00": 5,
    "17:45": 6,
    "19:30": 7,
}


class BellSlotDTO(BaseModel):
    slot_number: int = Field(..., ge=1, le=7, description="Номер пары от 1 до 7")
    start_time: str = Field(..., description="Время начала пары, напр. 08:30")
    end_time: str = Field(..., description="Время окончания пары, напр. 10:00")
    label: str = Field(..., description="Текстовое отображение интервала, напр. 08:30 - 10:00")


DEFAULT_BELLS: List[BellSlotDTO] = [
    BellSlotDTO(
        slot_number=num,
        start_time=start,
        end_time=end,
        label=f"{start} - {end}",
    )
    for num, (start, end) in SLOT_BELLS.items()
]


class BaseSlotDTO(BaseModel):
    id: str = Field(..., description="Уникальный ID слота, напр. MON_1")
    day_of_week: DayOfWeek = Field(..., description="День недели MONDAY..SATURDAY")
    slot_number: int = Field(..., ge=1, le=7, description="Номер пары от 1 до 7")
    start_time: Optional[str] = Field(default=None, description="Время начала пары (08:30)")
    end_time: Optional[str] = Field(default=None, description="Время окончания пары (10:00)")

    @model_validator(mode="after")
    def populate_bell_times(self) -> "BaseSlotDTO":
        if self.slot_number in SLOT_BELLS:
            bell_start, bell_end = SLOT_BELLS[self.slot_number]
            if not self.start_time:
                self.start_time = bell_start
            if not self.end_time:
                self.end_time = bell_end
        return self


class RoomDTO(BaseModel):
    id: str = Field(..., description="ID аудитории, напр. R101")
    name: str = Field(..., description="Название или номер, напр. 402а")
    capacity: int = Field(..., gt=0, description="Вместимость аудитории")
    features: List[str] = Field(default_factory=list, description="Теги оборудования: COMPUTERS, PROJECTOR и т.д.")


class TeacherDTO(BaseModel):
    id: str = Field(..., description="ID преподавателя")
    name: str = Field(..., description="ФИО преподавателя")
    unavailable_slots: List[str] = Field(default_factory=list, description="ID слотов, когда препод жестко занят")
    preferred_slots: List[str] = Field(default_factory=list, description="Желательные слоты (soft)")
    unwanted_slots: List[str] = Field(default_factory=list, description="Нежелательные слоты (soft)")


class AtomicGroupDTO(BaseModel):
    id: str = Field(..., description="ID атомарной подгруппы, напр. ИС-21-П1")
    name: str = Field(..., description="Название подгруппы")
    parent_group: str = Field(..., description="Родительская академическая группа, напр. ИС-21")
    student_count: int = Field(..., gt=0, description="Количество студентов")


class ExternalBlockDTO(BaseModel):
    id: str = Field(..., description="ID внешней блокировки")
    target_type: TargetType = Field(..., description="TEACHER или ATOMIC_GROUP")
    target_id: str = Field(..., description="ID преподавателя или подгруппы")
    slot_id: str = Field(..., description="ID слота")
    frequency: WeekFrequency = Field(default=WeekFrequency.WEEKLY, description="Частота блокировки")
    reason: str = Field(default="", description="Причина блокировки")


class LessonInputDTO(BaseModel):
    id: str = Field(..., description="ID занятия")
    subject: str = Field(..., description="Название дисциплины")
    teacher_id: str = Field(..., description="ID преподавателя")
    teacher_name: Optional[str] = Field(default=None, description="ФИО преподавателя (опционально)")
    atomic_group_ids: List[str] = Field(..., min_length=1, description="Список ID атомарных групп")
    student_count: int = Field(..., gt=0, description="Количество студентов")
    frequency: WeekFrequency = Field(default=WeekFrequency.WEEKLY, description="WEEKLY, NUMERATOR или DENOMINATOR")
    required_features: List[str] = Field(default_factory=list, description="Требуемое оборудование")
    pinned: bool = Field(default=False, description="Зафиксировано ли занятие вручную")
    pinned_slot_id: Optional[str] = Field(default=None, description="Фиксированный слот (если pinned=True)")
    pinned_room_id: Optional[str] = Field(default=None, description="Фиксированная аудитория (если pinned=True)")
    pinned_room_name: Optional[str] = Field(default=None, description="Имя фиксированной аудитории (опционально)")
    start_time: Optional[str] = Field(default=None, description="Время начала занятия")
    end_time: Optional[str] = Field(default=None, description="Время окончания занятия")


class SolveRequest(BaseModel):
    slots: List[BaseSlotDTO]
    rooms: List[RoomDTO]
    teachers: List[TeacherDTO]
    atomic_groups: List[AtomicGroupDTO]
    external_blocks: List[ExternalBlockDTO] = Field(default_factory=list)
    lessons: List[LessonInputDTO]
    solver_timeout_seconds: int = Field(default=30, ge=1, le=300, description="Лимит времени работы решателя")
    bells: List[BellSlotDTO] = Field(default_factory=lambda: list(DEFAULT_BELLS), description="Справочник времени звонков")


class LessonOutputDTO(BaseModel):
    id: str
    subject: str
    teacher_id: str
    teacher_name: Optional[str] = None
    atomic_group_ids: List[str]
    student_count: int
    frequency: WeekFrequency
    required_features: List[str] = Field(default_factory=list)
    pinned: bool
    slot_id: Optional[str] = None
    room_id: Optional[str] = None
    room_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class ConstraintMatchDTO(BaseModel):
    constraint_name: str
    score: str
    description: str


class ScoreExplanationDTO(BaseModel):
    hard_score: int
    soft_score: int
    is_feasible: bool
    summary: str
    violations: List[ConstraintMatchDTO] = Field(default_factory=list)


class SolveResultResponse(BaseModel):
    job_id: str
    status: str  # QUEUED, SOLVING, COMPLETED, FAILED
    score: Optional[str] = None
    lessons: List[LessonOutputDTO] = Field(default_factory=list)
    explanation: Optional[ScoreExplanationDTO] = None
    error_message: Optional[str] = None
    slots: List[BaseSlotDTO] = Field(default_factory=list, description="Полный справочник слотов")
    rooms: List[RoomDTO] = Field(default_factory=list, description="Полный справочник аудиторий")
    teachers: List[TeacherDTO] = Field(default_factory=list, description="Полный справочник преподавателей")
    atomic_groups: List[AtomicGroupDTO] = Field(default_factory=list, description="Полный справочник групп")
    bells: List[BellSlotDTO] = Field(default_factory=lambda: list(DEFAULT_BELLS), description="Справочник звонков")
