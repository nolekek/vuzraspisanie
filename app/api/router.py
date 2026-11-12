import json
import os
from pathlib import Path
import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.api.schemas import (
    SolveRequest,
    SolveResultResponse,
    BellSlotDTO,
    DEFAULT_BELLS,
)
from app.generator.synthetic import SyntheticDepartmentGenerator
from app.generator.uspu_parser import uspu_parser
from app.solver.service import solver_service

router = APIRouter(prefix="/api/v1/schedules", tags=["Schedules"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
USPU_DATA_PATH = BASE_DIR / "data" / "uspu_schedule.json"


def _get_uspu_path() -> Path:
    if USPU_DATA_PATH.exists():
        return USPU_DATA_PATH
    return Path("data/uspu_schedule.json")


class ParseUSPURequest(BaseModel):
    groups: List[str] = Field(
        default=["АИ-2431", "АИ-2331"],
        description="Список групп УрГПУ для парсинга с https://uspu.ru/education/eios/schedule/",
    )
    pin_ratio: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Доля зафиксированных (pinned) пар",
    )


@router.get("/bells", response_model=List[BellSlotDTO])
def get_bell_schedule():
    """Справочник времени академических пар вуза (1..7 пары)."""
    return DEFAULT_BELLS


@router.post("/solve", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def solve_schedule_async(req: SolveRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    solver_service.jobs[job_id] = SolveResultResponse(
        job_id=job_id,
        status="QUEUED",
        lessons=[],
        slots=req.slots,
        rooms=req.rooms,
        teachers=req.teachers,
        atomic_groups=req.atomic_groups,
        bells=req.bells or list(DEFAULT_BELLS),
    )
    background_tasks.add_task(solver_service.start_async_solve, job_id, req)
    return {
        "job_id": job_id,
        "status": "QUEUED",
        "message": f"Optimization job {job_id} successfully queued with timeout {req.solver_timeout_seconds}s.",
    }


@router.get("/{job_id}/result", response_model=SolveResultResponse)
async def get_schedule_result(job_id: str):
    res = solver_service.get_job(job_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization job with id '{job_id}' not found.",
        )
    return res


@router.post("/solve-sync", response_model=SolveResultResponse)
async def solve_schedule_sync(req: SolveRequest):
    return solver_service.solve_sync(req)


@router.get("/datasets/list")
def list_datasets():
    uspu_path = _get_uspu_path()
    uspu_available = uspu_path.exists()
    return [
        {
            "id": "synthetic_small",
            "name": "Синтетический (Мини: 2 группы, 6 занятий)",
            "description": "Быстрый тест для мгновенной проверки (2-3 сек)",
        },
        {
            "id": "synthetic_standard",
            "name": "Синтетический (Кафедра: 6 групп, 12 подгрупп, 48 занятий)",
            "description": "Полномасштабная нагрузка кафедры с 15 преподавателями и 10 аудиториями",
        },
        {
            "id": "uspu_real",
            "name": "Реальное расписание УрГПУ (uspu.ru: ИнЯз 47 занятий)",
            "description": "Спарсенные живые данные с официального портала УрГПУ",
            "available": uspu_available,
        },
    ]


@router.get("/datasets/{preset_id}", response_model=SolveRequest)
def get_dataset(preset_id: str):
    gen = SyntheticDepartmentGenerator(seed=42)
    if preset_id == "synthetic_small":
        req, _ = gen.generate_perfect_schedule_and_problem(
            num_academic_groups=2,
            num_teachers=4,
            num_rooms=3,
            lessons_per_group=3,
            pin_ratio=0.2,
        )
        req.solver_timeout_seconds = 5
        return req
    elif preset_id == "synthetic_standard":
        req, _ = gen.generate_perfect_schedule_and_problem(
            num_academic_groups=6,
            num_teachers=15,
            num_rooms=10,
            lessons_per_group=8,
            pin_ratio=0.15,
        )
        req.solver_timeout_seconds = 15
        return req
    elif preset_id == "uspu_real":
        uspu_file = _get_uspu_path()
        if not uspu_file.exists():
            req = uspu_parser.parse_groups(["АИ-2431", "АИ-2331"], pin_ratio=0.25)
            uspu_file.parent.mkdir(parents=True, exist_ok=True)
            with open(uspu_file, "w", encoding="utf-8") as f:
                json.dump(req.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
            return req
        with open(uspu_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SolveRequest.model_validate(data)
    else:
        raise HTTPException(status_code=404, detail=f"Dataset preset '{preset_id}' not found.")


@router.post("/parse-uspu", response_model=SolveRequest)
def parse_uspu_live(req: ParseUSPURequest):
    """Парсит в реальном времени расписание с uspu.ru/education/eios/schedule/ для указанных групп."""
    try:
        parsed_problem = uspu_parser.parse_groups(group_names=req.groups, pin_ratio=req.pin_ratio)
        return parsed_problem
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка парсинга расписания с uspu.ru: {str(e)}",
        )
