import pytest
from timefold.solver.test import ConstraintVerifier
from timefold.solver.score import HardSoftScore

from app.domain import (
    TimetableSolution,
    Lesson,
    Room,
    BaseSlot,
    Teacher,
    ExternalBlock,
    DayOfWeek,
    WeekFrequency,
    TargetType,
)
from app.solver.constraints import define_constraints


@pytest.fixture
def verifier():
    return ConstraintVerifier.build(define_constraints, TimetableSolution, Lesson)


@pytest.fixture
def base_slot():
    return BaseSlot(id="MON_1", day_of_week=DayOfWeek.MONDAY, slot_number=1)


@pytest.fixture
def base_room():
    return Room(id="R101", name="101", capacity=30, features=["PROJECTOR"])


def test_room_conflict_weekly(verifier, base_slot, base_room):
    l1 = Lesson(id="L1", subject="Math", teacher_id="T1", atomic_group_ids=["G1"], student_count=20, frequency=WeekFrequency.WEEKLY, timeslot=base_slot, room=base_room)
    l2 = Lesson(id="L2", subject="CS", teacher_id="T2", atomic_group_ids=["G2"], student_count=20, frequency=WeekFrequency.WEEKLY, timeslot=base_slot, room=base_room)

    # 1 штраф за конфликт аудитории
    verifier.verify_that().given(l1, l2).scores(HardSoftScore.of_hard(-1))


def test_numerator_denominator_no_conflict(verifier, base_slot, base_room):
    # Числитель и знаменатель в одной аудитории и в одном слоте НЕ конфликтуют!
    l1 = Lesson(id="L1", subject="Math", teacher_id="T1", atomic_group_ids=["G1"], student_count=20, frequency=WeekFrequency.NUMERATOR, timeslot=base_slot, room=base_room)
    l2 = Lesson(id="L2", subject="CS", teacher_id="T2", atomic_group_ids=["G2"], student_count=20, frequency=WeekFrequency.DENOMINATOR, timeslot=base_slot, room=base_room)

    verifier.verify_that().given(l1, l2).scores(HardSoftScore.of_hard(0))


def test_atomic_group_conflict(verifier, base_slot, base_room):
    # Две подгруппы или поток пересекаются по атомарному юниту
    r2 = Room(id="R102", name="102", capacity=30, features=["PROJECTOR"])
    l1 = Lesson(id="L1", subject="Math", teacher_id="T1", atomic_group_ids=["ИС-21-П1", "ИС-21-П2"], student_count=30, frequency=WeekFrequency.WEEKLY, timeslot=base_slot, room=base_room)
    l2 = Lesson(id="L2", subject="English", teacher_id="T2", atomic_group_ids=["ИС-21-П1"], student_count=15, frequency=WeekFrequency.WEEKLY, timeslot=base_slot, room=r2)

    # Аудитории разные, преподы разные, но у группы ИС-21-П1 накладка!
    verifier.verify_that().given(l1, l2).scores(HardSoftScore.of_hard(-1))


def test_room_capacity_violation(verifier, base_slot):
    small_room = Room(id="R_TINY", name="Tiny Room", capacity=15, features=["PROJECTOR"])
    l1 = Lesson(id="L1", subject="Math", teacher_id="T1", atomic_group_ids=["G1"], student_count=25, frequency=WeekFrequency.WEEKLY, timeslot=base_slot, room=small_room)

    # 25 студентов в комнате на 15 = штраф -10 hard
    verifier.verify_that().given(l1).scores(HardSoftScore.of_hard(-10))


def test_missing_required_equipment(verifier, base_slot):
    no_pc_room = Room(id="R_NO_PC", name="Simple Room", capacity=40, features=["PROJECTOR"])
    l1 = Lesson(id="L1", subject="Programming", teacher_id="T1", atomic_group_ids=["G1"], student_count=20, frequency=WeekFrequency.WEEKLY, required_features=["COMPUTERS"], timeslot=base_slot, room=no_pc_room)

    # Нет компьютеров = -1 hard
    verifier.verify_that().given(l1).scores(HardSoftScore.of_hard(-1))
