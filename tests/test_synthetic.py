from app.generator.synthetic import SyntheticDepartmentGenerator


def test_synthetic_reverse_generation():
    generator = SyntheticDepartmentGenerator(seed=123)
    request, ground_truth = generator.generate_perfect_schedule_and_problem(
        num_academic_groups=4,
        num_teachers=10,
        num_rooms=8,
        lessons_per_group=6,
        pin_ratio=0.2,
    )

    assert len(request.slots) == 25  # 5 days * 5 slots
    assert len(request.rooms) == 8
    assert len(request.teachers) == 10
    assert len(request.atomic_groups) == 8  # 4 groups * 2 subgroups
    assert len(request.lessons) > 0
    assert len(ground_truth) == len(request.lessons)

    pinned_count = sum(1 for l in request.lessons if l.pinned)
    assert pinned_count > 0, "Должны присутствовать зафиксированные пары"
