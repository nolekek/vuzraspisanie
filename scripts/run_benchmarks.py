import time
from app.generator.synthetic import SyntheticDepartmentGenerator
from app.solver.service import solver_service


def run_benchmark():
    print("=" * 60)
    print("🚀 КАФЕДРАЛЬНЫЙ БЕНЧМАРК ОПТИМИЗАЦИИ РАСПИСАНИЯ (Timefold)")
    print("=" * 60)

    gen = SyntheticDepartmentGenerator(seed=101)
    print("📦 Генерация синтетических данных кафедры методом 'Reverse Generation'...")
    req, ground_truth = gen.generate_perfect_schedule_and_problem(
        num_academic_groups=6,
        num_teachers=15,
        num_rooms=10,
        lessons_per_group=8,
        pin_ratio=0.15,
    )
    req.solver_timeout_seconds = 15

    pinned_count = sum(1 for l in req.lessons if l.pinned)
    print(f"📊 Параметры задачи:")
    print(f"   - Академических групп: 6 (Атомарных подгрупп: {len(req.atomic_groups)})")
    print(f"   - Преподавателей: {len(req.teachers)}")
    print(f"   - Аудиторий: {len(req.rooms)}")
    print(f"   - Базовых слотов: {len(req.slots)} (2-недельный цикл)")
    print(f"   - Всего занятий: {len(req.lessons)} (из них зафиксировано методистом pinned: {pinned_count})")
    print(f"   - Лимит решателя: {req.solver_timeout_seconds} сек")
    print("=" * 60)

    print("🧠 Запуск оптимизатора Timefold Solver...")
    t0 = time.time()
    res = solver_service.solve_sync(req)
    elapsed = time.time() - t0

    print("=" * 60)
    print(f"🏁 РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ (затрачено: {elapsed:.2f} сек):")
    print(f"   - Статус: {res.status}")
    print(f"   - Итоговый Score: {res.score}")
    print(f"   - Hard Score: {res.explanation.hard_score} (Feasible: {res.explanation.is_feasible})")
    print(f"   - Soft Score: {res.explanation.soft_score}")
    print("=" * 60)

    print("📋 Фрагмент расставленных занятий (первые 5 пар):")
    for l in res.lessons[:5]:
        pin_mark = "[PINNED]" if l.pinned else "        "
        subs = ",".join(l.atomic_group_ids)
        print(f"   {pin_mark} {l.id} | {l.subject:<22} | Слот: {l.slot_id} | Ауд: {l.room_id} | Подгр: {subs} ({l.frequency.value})")

    print("=" * 60)
    print("🔍 Сводка штрафов и совпадений (Score Explanation):")
    for line in res.explanation.summary.strip().split("\n")[:15]:
        print(f"   {line}")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmark()
