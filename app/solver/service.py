import asyncio
import uuid
from typing import Dict, Optional

from timefold.solver.config import (
    SolverConfig,
    ScoreDirectorFactoryConfig,
    TerminationConfig,
    Duration,
)
from timefold.solver import SolverFactory, SolutionManager

from app.api.schemas import (
    SolveRequest,
    SolveResultResponse,
    LessonOutputDTO,
    ScoreExplanationDTO,
    ConstraintMatchDTO,
    SLOT_BELLS,
    DEFAULT_BELLS,
)
from app.domain import (
    BaseSlot,
    Room,
    Teacher,
    AtomicGroup,
    ExternalBlock,
    Lesson,
    TimetableSolution,
)
from app.solver.constraints import define_constraints


class SolverService:
    def __init__(self):
        self.jobs: Dict[str, SolveResultResponse] = {}

    def _build_solver_factory(self, timeout_seconds: int) -> SolverFactory:
        config = SolverConfig(
            solution_class=TimetableSolution,
            entity_class_list=[Lesson],
            score_director_factory_config=ScoreDirectorFactoryConfig(
                constraint_provider_function=define_constraints
            ),
            termination_config=TerminationConfig(spent_limit=Duration(seconds=timeout_seconds)),
        )
        return SolverFactory.create(config)

    def request_to_solution(self, req: SolveRequest) -> TimetableSolution:
        slots = [
            BaseSlot(id=s.id, day_of_week=s.day_of_week, slot_number=s.slot_number)
            for s in req.slots
        ]
        slot_map = {s.id: s for s in slots}

        rooms = [
            Room(id=r.id, name=r.name, capacity=r.capacity, features=r.features)
            for r in req.rooms
        ]
        room_map = {r.id: r for r in rooms}

        teachers = [
            Teacher(
                id=t.id,
                name=t.name,
                unavailable_slots=t.unavailable_slots,
                preferred_slots=t.preferred_slots,
                unwanted_slots=t.unwanted_slots,
            )
            for t in req.teachers
        ]

        atomic_groups = [
            AtomicGroup(
                id=g.id,
                name=g.name,
                parent_group=g.parent_group,
                student_count=g.student_count,
            )
            for g in req.atomic_groups
        ]

        external_blocks = [
            ExternalBlock(
                id=b.id,
                target_type=b.target_type,
                target_id=b.target_id,
                slot_id=b.slot_id,
                frequency=b.frequency,
                reason=b.reason,
            )
            for b in req.external_blocks
        ]

        lessons = []
        for l in req.lessons:
            pinned_slot = slot_map.get(l.pinned_slot_id) if l.pinned_slot_id else None
            pinned_room = room_map.get(l.pinned_room_id) if l.pinned_room_id else None

            lesson = Lesson(
                id=l.id,
                subject=l.subject,
                teacher_id=l.teacher_id,
                atomic_group_ids=l.atomic_group_ids,
                student_count=l.student_count,
                frequency=l.frequency,
                required_features=l.required_features,
                pinned=l.pinned,
                timeslot=pinned_slot,
                room=pinned_room,
            )
            lessons.append(lesson)

        return TimetableSolution(
            id=str(uuid.uuid4()),
            timeslots=slots,
            rooms=rooms,
            teachers=teachers,
            atomic_groups=atomic_groups,
            external_blocks=external_blocks,
            lessons=lessons,
        )

    def solve_sync(self, req: SolveRequest) -> SolveResultResponse:
        problem = self.request_to_solution(req)
        factory = self._build_solver_factory(req.solver_timeout_seconds)
        solver = factory.build_solver()
        solution_manager = SolutionManager.create(factory)

        best_solution = solver.solve(problem)
        score = best_solution.score
        explanation = solution_manager.explain(best_solution)

        teacher_map = {t.id: t.name for t in req.teachers}
        room_map = {r.id: r.name for r in req.rooms}
        slot_map = {s.id: s for s in req.slots}

        output_lessons = []
        for l in best_solution.lessons:
            slot_id = l.timeslot.id if l.timeslot else None
            room_id = l.room.id if l.room else None

            teacher_name = teacher_map.get(l.teacher_id, l.teacher_id)
            room_name = (
                l.room.name
                if l.room and hasattr(l.room, "name")
                else (room_map.get(room_id, room_id) if room_id else None)
            )

            start_t = None
            end_t = None
            if slot_id and slot_id in slot_map:
                s_dto = slot_map[slot_id]
                start_t = s_dto.start_time
                end_t = s_dto.end_time
            elif l.timeslot and l.timeslot.slot_number in SLOT_BELLS:
                start_t, end_t = SLOT_BELLS[l.timeslot.slot_number]

            output_lessons.append(
                LessonOutputDTO(
                    id=l.id,
                    subject=l.subject,
                    teacher_id=l.teacher_id,
                    teacher_name=teacher_name,
                    atomic_group_ids=l.atomic_group_ids,
                    student_count=l.student_count,
                    frequency=l.frequency,
                    required_features=l.required_features,
                    pinned=l.pinned,
                    slot_id=slot_id,
                    room_id=room_id,
                    room_name=room_name,
                    start_time=start_t,
                    end_time=end_t,
                )
            )

        explanation_dto = ScoreExplanationDTO(
            hard_score=score.hard_score if score else 0,
            soft_score=score.soft_score if score else 0,
            is_feasible=score.is_feasible if score else False,
            summary=explanation.summary if explanation else "",
            violations=[],
        )

        return SolveResultResponse(
            job_id=str(uuid.uuid4()),
            status="COMPLETED",
            score=str(score),
            lessons=output_lessons,
            explanation=explanation_dto,
            slots=req.slots,
            rooms=req.rooms,
            teachers=req.teachers,
            atomic_groups=req.atomic_groups,
            bells=req.bells or list(DEFAULT_BELLS),
        )

    async def start_async_solve(self, job_id: str, req: SolveRequest):
        self.jobs[job_id] = SolveResultResponse(
            job_id=job_id,
            status="SOLVING",
            lessons=[],
            slots=req.slots,
            rooms=req.rooms,
            teachers=req.teachers,
            atomic_groups=req.atomic_groups,
            bells=req.bells or list(DEFAULT_BELLS),
        )

        try:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, self.solve_sync, req)
            res.job_id = job_id
            self.jobs[job_id] = res
        except Exception as e:
            self.jobs[job_id] = SolveResultResponse(
                job_id=job_id,
                status="FAILED",
                error_message=str(e),
                slots=req.slots,
                rooms=req.rooms,
                teachers=req.teachers,
                atomic_groups=req.atomic_groups,
                bells=req.bells or list(DEFAULT_BELLS),
            )

    def get_job(self, job_id: str) -> Optional[SolveResultResponse]:
        return self.jobs.get(job_id)


solver_service = SolverService()
