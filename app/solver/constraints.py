from typing import List
from timefold.solver.score import (
    constraint_provider,
    HardSoftScore,
    Joiners,
    ConstraintFactory,
)

from app.domain.enums import TargetType, WeekFrequency, overlaps_week
from app.domain.models import Room, Teacher, ExternalBlock, BaseSlot
from app.domain.solution import Lesson


def has_atomic_group_conflict(groups1: List[str], groups2: List[str]) -> bool:
    for g in groups1:
        if g in groups2:
            return True
    return False


def is_single_slot_window(s1: BaseSlot, s2: BaseSlot) -> bool:
    return abs(s1.slot_number - s2.slot_number) == 2


@constraint_provider
def define_constraints(cf: ConstraintFactory):
    return [
        # =========================================================================
        # 1. HARD CONSTRAINTS
        # =========================================================================

        # 1.1 Конфликт аудитории: одна аудитория не может принимать 2 пары одновременно
        cf.for_each_unique_pair(
            Lesson,
            Joiners.equal(lambda l: l.room),
            Joiners.equal(lambda l: l.timeslot),
        )
        .filter(
            lambda l1, l2: (
                l1.room is not None
                and l1.timeslot is not None
                and overlaps_week(l1.frequency, l2.frequency)
            )
        )
        .penalize(HardSoftScore.ONE_HARD)
        .as_constraint("Room conflict"),

        # 1.2 Конфликт преподавателя: преподаватель не может вести 2 пары одновременно
        cf.for_each_unique_pair(
            Lesson,
            Joiners.equal(lambda l: l.teacher_id),
            Joiners.equal(lambda l: l.timeslot),
        )
        .filter(
            lambda l1, l2: (
                l1.timeslot is not None
                and overlaps_week(l1.frequency, l2.frequency)
            )
        )
        .penalize(HardSoftScore.ONE_HARD)
        .as_constraint("Teacher conflict"),

        # 1.3 Конфликт студентов: атомарная подгруппа не может учиться на двух парах сразу
        cf.for_each_unique_pair(
            Lesson,
            Joiners.equal(lambda l: l.timeslot),
        )
        .filter(
            lambda l1, l2: (
                l1.timeslot is not None
                and overlaps_week(l1.frequency, l2.frequency)
                and has_atomic_group_conflict(l1.atomic_group_ids, l2.atomic_group_ids)
            )
        )
        .penalize(HardSoftScore.ONE_HARD)
        .as_constraint("Student atomic group conflict"),

        # 1.4 Вместимость аудитории: число студентов не должно превышать capacity
        cf.for_each(Lesson)
        .filter(
            lambda l: l.room is not None and l.room.capacity < l.student_count
        )
        .penalize(
            HardSoftScore.ONE_HARD,
            lambda l: l.student_count - l.room.capacity,
        )
        .as_constraint("Room capacity violation"),

        # 1.5 Оборудование аудитории: аудитория должна обладать всеми требуемыми features
        cf.for_each(Lesson)
        .filter(
            lambda l: l.room is not None and not l.room.has_features(l.required_features)
        )
        .penalize(HardSoftScore.ONE_HARD)
        .as_constraint("Missing required room features"),

        # 1.6 Недоступные слоты преподавателя (занятость на других кафедрах/днях)
        cf.for_each(Lesson)
        .join(Teacher, Joiners.equal(lambda l: l.teacher_id, lambda t: t.id))
        .filter(
            lambda l, t: l.timeslot is not None and l.timeslot.id in t.unavailable_slots
        )
        .penalize(HardSoftScore.ONE_HARD)
        .as_constraint("Teacher unavailable slot"),

        # 1.7 Внешние блокировки преподавателей (пары в общевузовском расписании)
        cf.for_each(Lesson)
        .join(
            ExternalBlock,
            Joiners.equal(lambda l: l.teacher_id, lambda b: b.target_id),
            Joiners.equal(lambda l: l.timeslot.id if l.timeslot else None, lambda b: b.slot_id),
        )
        .filter(
            lambda l, b: (
                b.target_type == TargetType.TEACHER
                and l.timeslot is not None
                and overlaps_week(l.frequency, b.frequency)
            )
        )
        .penalize(HardSoftScore.ONE_HARD)
        .as_constraint("External block teacher"),

        # 1.8 Внешние блокировки студенческих групп (военка, общевузовские потоки)
        cf.for_each(Lesson)
        .join(
            ExternalBlock,
            Joiners.equal(lambda l: l.timeslot.id if l.timeslot else None, lambda b: b.slot_id),
        )
        .filter(
            lambda l, b: (
                b.target_type == TargetType.ATOMIC_GROUP
                and l.timeslot is not None
                and b.target_id in l.atomic_group_ids
                and overlaps_week(l.frequency, b.frequency)
            )
        )
        .penalize(HardSoftScore.ONE_HARD)
        .as_constraint("External block student group"),

        # =========================================================================
        # 2. SOFT CONSTRAINTS (Оптимизация качества жизни)
        # =========================================================================

        # 2.1 Пожелания преподавателей: штраф за нежелательный слот
        cf.for_each(Lesson)
        .join(Teacher, Joiners.equal(lambda l: l.teacher_id, lambda t: t.id))
        .filter(
            lambda l, t: l.timeslot is not None and l.timeslot.id in t.unwanted_slots
        )
        .penalize(HardSoftScore.ONE_SOFT, lambda l, t: 5)
        .as_constraint("Teacher unwanted slot"),

        # 2.2 Пожелания преподавателей: поощрение за желаемый слот
        cf.for_each(Lesson)
        .join(Teacher, Joiners.equal(lambda l: l.teacher_id, lambda t: t.id))
        .filter(
            lambda l, t: l.timeslot is not None and l.timeslot.id in t.preferred_slots
        )
        .reward(HardSoftScore.ONE_SOFT, lambda l, t: 5)
        .as_constraint("Teacher preferred slot"),

        # 2.3 Синхронизация подгрупп: лабораторные/практики подгрупп одной группы ставить в один слот!
        cf.for_each_unique_pair(
            Lesson,
            Joiners.equal(lambda l: l.timeslot),
        )
        .filter(
            lambda l1, l2: (
                l1.timeslot is not None
                and l1.room != l2.room
                and l1.subject == l2.subject
                and len(l1.atomic_group_ids) == 1
                and len(l2.atomic_group_ids) == 1
                and l1.atomic_group_ids[0].rsplit("-", 1)[0] == l2.atomic_group_ids[0].rsplit("-", 1)[0]
                and overlaps_week(l1.frequency, l2.frequency)
            )
        )
        .reward(HardSoftScore.ONE_SOFT, lambda l1, l2: 10)
        .as_constraint("Subgroup parallel synchronization"),

        # 2.4 Минимизация окон у преподавателей: штраф за дыры в течение одного дня
        cf.for_each_unique_pair(
            Lesson,
            Joiners.equal(lambda l: l.teacher_id),
            Joiners.equal(lambda l: l.timeslot.day_of_week if l.timeslot else None),
        )
        .filter(
            lambda l1, l2: (
                l1.timeslot is not None
                and l2.timeslot is not None
                and overlaps_week(l1.frequency, l2.frequency)
                and is_single_slot_window(l1.timeslot, l2.timeslot)  # Двойка означает дыру ровно в 1 пару!
            )
        )
        .penalize(HardSoftScore.ONE_SOFT, lambda l1, l2: 3)
        .as_constraint("Teacher 1-slot window gap"),

        # 2.5 Минимизация окон у студентов (для каждой атомарной группы): штраф за дыру ровно в 1 пару
        cf.for_each_unique_pair(
            Lesson,
            Joiners.equal(lambda l: l.timeslot.day_of_week if l.timeslot else None),
        )
        .filter(
            lambda l1, l2: (
                l1.timeslot is not None
                and l2.timeslot is not None
                and overlaps_week(l1.frequency, l2.frequency)
                and has_atomic_group_conflict(l1.atomic_group_ids, l2.atomic_group_ids)
                and is_single_slot_window(l1.timeslot, l2.timeslot)
            )
        )
        .penalize(HardSoftScore.ONE_SOFT, lambda l1, l2: 5)
        .as_constraint("Student 1-slot window gap"),
    ]
