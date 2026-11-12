import time
from fastapi.testclient import TestClient

from app.main import app
from app.generator.synthetic import SyntheticDepartmentGenerator

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Timefold Solver" in data["engine"]


def test_solve_sync_endpoint():
    generator = SyntheticDepartmentGenerator(seed=77)
    req, ground_truth = generator.generate_perfect_schedule_and_problem(
        num_academic_groups=2,
        num_teachers=4,
        num_rooms=3,
        lessons_per_group=3,
        pin_ratio=0.25,
    )
    req.solver_timeout_seconds = 4

    payload = req.model_dump(mode="json")
    response = client.post("/api/v1/schedules/solve-sync", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["score"] is not None
    assert "0hard" in data["score"]  # Обязательно 0 hard нарушений!
    assert len(data["lessons"]) == len(req.lessons)

    # Проверяем, что все занятия получили слот и аудиторию
    for lesson in data["lessons"]:
        assert lesson["slot_id"] is not None
        assert lesson["room_id"] is not None

    # Проверяем, что pinned занятия остались на своих местах
    for original_lesson in req.lessons:
        if original_lesson.pinned:
            placed = next(l for l in data["lessons"] if l["id"] == original_lesson.id)
            assert placed["slot_id"] == original_lesson.pinned_slot_id
            assert placed["room_id"] == original_lesson.pinned_room_id


def test_solve_async_workflow():
    generator = SyntheticDepartmentGenerator(seed=88)
    req, _ = generator.generate_perfect_schedule_and_problem(
        num_academic_groups=2,
        num_teachers=3,
        num_rooms=3,
        lessons_per_group=2,
        pin_ratio=0.2,
    )
    req.solver_timeout_seconds = 3

    payload = req.model_dump(mode="json")
    post_res = client.post("/api/v1/schedules/solve", json=payload)
    assert post_res.status_code == 202

    post_data = post_res.json()
    job_id = post_data["job_id"]
    assert job_id is not None
    assert post_data["status"] == "QUEUED"

    # Опрашиваем результат
    max_retries = 15
    completed = False
    for _ in range(max_retries):
        time.sleep(1)
        get_res = client.get(f"/api/v1/schedules/{job_id}/result")
        assert get_res.status_code == 200
        get_data = get_res.json()
        if get_data["status"] == "COMPLETED":
            completed = True
            assert get_data["score"] is not None
            assert len(get_data["lessons"]) > 0
            break
        elif get_data["status"] == "FAILED":
            pytest.fail(f"Job failed: {get_data.get('error_message')}")

    assert completed, "Фоновая задача оптимизации не успела завершиться за отведенное время."


def test_not_found_job():
    res = client.get("/api/v1/schedules/00000000-0000-0000-0000-000000000000/result")
    assert res.status_code == 404
