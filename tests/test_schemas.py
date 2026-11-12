import pytest
from app.api.schemas import (
    BaseSlotDTO,
    RoomDTO,
    TeacherDTO,
    AtomicGroupDTO,
    ExternalBlockDTO,
    LessonInputDTO,
    SolveRequest,
)
from app.domain.enums import DayOfWeek, WeekFrequency, TargetType
from app.solver.service import solver_service


def test_solve_request_serialization():
    req = SolveRequest(
        slots=[BaseSlotDTO(id="MON_1", day_of_week=DayOfWeek.MONDAY, slot_number=1)],
        rooms=[RoomDTO(id="R1", name="101", capacity=30, features=["PROJECTOR"])],
        teachers=[TeacherDTO(id="T1", name="Иванов И.И.")],
        atomic_groups=[AtomicGroupDTO(id="ИС-21-П1", name="ИС-21 Подгруппа 1", parent_group="ИС-21", student_count=15)],
        external_blocks=[],
        lessons=[
            LessonInputDTO(
                id="L1",
                subject="Математика",
                teacher_id="T1",
                atomic_group_ids=["ИС-21-П1"],
                student_count=15,
                frequency=WeekFrequency.WEEKLY,
                required_features=["PROJECTOR"],
                pinned=True,
                pinned_slot_id="MON_1",
                pinned_room_id="R1",
            )
        ],
        solver_timeout_seconds=10,
    )

    data = req.model_dump()
    assert data["solver_timeout_seconds"] == 10
    assert len(data["lessons"]) == 1
    assert data["lessons"][0]["pinned"] is True

    # Test conversion to Timefold domain solution
    solution = solver_service.request_to_solution(req)
    assert len(solution.timeslots) == 1
    assert len(solution.lessons) == 1
    assert solution.lessons[0].pinned is True
    assert solution.lessons[0].timeslot.id == "MON_1"
    assert solution.lessons[0].room.id == "R1"
