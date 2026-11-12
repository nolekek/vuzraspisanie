import random
from typing import List, Tuple, Dict, Set
from app.domain.enums import DayOfWeek, WeekFrequency, TargetType
from app.api.schemas import (
    BaseSlotDTO,
    RoomDTO,
    TeacherDTO,
    AtomicGroupDTO,
    ExternalBlockDTO,
    LessonInputDTO,
    SolveRequest,
    SLOT_BELLS,
    DEFAULT_BELLS,
)


class SyntheticDepartmentGenerator:
    """Генератор синтетических данных кафедры методом 'обратной генерации' (Reverse Generation).

    Генерирует согласованное расписание кафедры (0 Hard violations),
    а затем стирает переменные планирования у не-pinned занятий.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_slots(self, days: int = 6, slots_per_day: int = 6) -> List[BaseSlotDTO]:
        weekdays = [
            DayOfWeek.MONDAY,
            DayOfWeek.TUESDAY,
            DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY,
            DayOfWeek.FRIDAY,
            DayOfWeek.SATURDAY,
        ][:days]
        slots = []
        for d in weekdays:
            for s in range(1, slots_per_day + 1):
                bell = SLOT_BELLS.get(s, ("08:30", "10:00"))
                slots.append(
                    BaseSlotDTO(
                        id=f"{d.value[:3]}_{s}",
                        day_of_week=d,
                        slot_number=s,
                        start_time=bell[0],
                        end_time=bell[1],
                    )
                )
        return slots

    def generate_rooms(self, count: int = 15) -> List[RoomDTO]:
        rooms = []
        for i in range(1, count + 1):
            if i <= 3:
                # Большие лекционные потоковые аудитории
                rooms.append(RoomDTO(id=f"R_LECT_{i}", name=f"Ауд. {100+i} (Поток)", capacity=120, features=["PROJECTOR"]))
            elif i <= 8:
                # Компьютерные классы кафедры
                rooms.append(RoomDTO(id=f"R_COMP_{i}", name=f"Ауд. {200+i} (Комп. класс)", capacity=30, features=["COMPUTERS", "PROJECTOR"]))
            elif i <= 10:
                # Специализированные научные лаборатории
                rooms.append(RoomDTO(id=f"R_LAB_{i}", name=f"Ауд. {300+i} (Лаб. ИИ)", capacity=25, features=["LAB_AI", "COMPUTERS"]))
            else:
                # Обычные аудитории для практик и семинаров
                rooms.append(RoomDTO(id=f"R_SEM_{i}", name=f"Ауд. {400+i} (Семинарская)", capacity=40, features=["PROJECTOR"]))
        return rooms

    def generate_teachers(self, count: int = 25, all_slots: List[BaseSlotDTO] = None) -> List[TeacherDTO]:
        slots = all_slots or self.generate_slots()
        slot_ids = [s.id for s in slots]
        teachers = []
        for i in range(1, count + 1):
            unavail = self.rng.sample(slot_ids, k=2) if len(slot_ids) >= 5 else []
            pref = self.rng.sample([s for s in slot_ids if s not in unavail], k=2) if len(slot_ids) >= 5 else []
            unwant = self.rng.sample([s for s in slot_ids if s not in unavail and s not in pref], k=2) if len(slot_ids) >= 5 else []
            teachers.append(
                TeacherDTO(
                    id=f"T_{i:02d}",
                    name=f"Профессор/Доцент {i}",
                    unavailable_slots=unavail,
                    preferred_slots=pref,
                    unwanted_slots=unwant,
                )
            )
        return teachers

    def generate_groups(self, academic_groups_count: int = 12) -> List[AtomicGroupDTO]:
        atomic_groups = []
        for g in range(1, academic_groups_count + 1):
            course = (g % 4) + 1
            parent_name = f"ПИ-{course}0{g}"
            # Каждая группа делится на 2 подгруппы
            atomic_groups.append(
                AtomicGroupDTO(id=f"{parent_name}_SUB1", name=f"{parent_name} (Подгр. 1)", parent_group=parent_name, student_count=15)
            )
            atomic_groups.append(
                AtomicGroupDTO(id=f"{parent_name}_SUB2", name=f"{parent_name} (Подгр. 2)", parent_group=parent_name, student_count=15)
            )
        return atomic_groups

    def generate_perfect_schedule_and_problem(
        self,
        num_academic_groups: int = 6,
        num_teachers: int = 15,
        num_rooms: int = 10,
        lessons_per_group: int = 8,
        pin_ratio: float = 0.15,
    ) -> Tuple[SolveRequest, Dict[str, Tuple[str, str]]]:
        """Обратная генерация (Reverse Generation):

        1. Строит заведомо валидное бесконфликтное расписание (Ground Truth).
        2. Формирует SolveRequest, затирая слот и аудиторию у (1 - pin_ratio) занятий.
        """
        slots = self.generate_slots(days=5, slots_per_day=5)
        rooms = self.generate_rooms(count=num_rooms)
        teachers = self.generate_teachers(count=num_teachers, all_slots=slots)
        groups = self.generate_groups(academic_groups_count=num_academic_groups)

        # Индексация занятости для гарантии 0 hard-конфликтов
        # key: (entity_id, slot_id, frequency)
        group_busy: Set[Tuple[str, str, WeekFrequency]] = set()
        teacher_busy: Set[Tuple[str, str, WeekFrequency]] = set()
        room_busy: Set[Tuple[str, str, WeekFrequency]] = set()

        lessons: List[LessonInputDTO] = []
        ground_truth: Dict[str, Tuple[str, str]] = {}
        lesson_counter = 1

        academic_group_names = sorted(list(set(g.parent_group for g in groups)))

        for grp_name in academic_group_names:
            subgroups = [g.id for g in groups if g.parent_group == grp_name]
            for l_idx in range(lessons_per_group):
                is_stream = (l_idx == 0 or l_idx == 1)
                is_half = not is_stream

                freq_choice = self.rng.random()
                if freq_choice < 0.6:
                    freq = WeekFrequency.WEEKLY
                elif freq_choice < 0.8:
                    freq = WeekFrequency.NUMERATOR
                else:
                    freq = WeekFrequency.DENOMINATOR

                target_subs = subgroups if is_stream else [self.rng.choice(subgroups)]
                st_count = 30 if is_stream else 15

                req_feats = []
                if is_stream:
                    req_feats.append("PROJECTOR")
                elif l_idx % 2 == 0:
                    req_feats.append("COMPUTERS")

                # Ищем валидный слот, преподавателя и аудиторию
                assigned_slot = None
                assigned_room = None
                assigned_teacher = None

                shuffled_slots = list(slots)
                self.rng.shuffle(shuffled_slots)

                for slot in shuffled_slots:
                    # Проверяем занятость подгрупп
                    slot_group_conflict = False
                    for sub in target_subs:
                        if (sub, slot.id, freq) in group_busy or (sub, slot.id, WeekFrequency.WEEKLY) in group_busy:
                            slot_group_conflict = True
                            break
                    if slot_group_conflict:
                        continue

                    # Ищем преподавателя
                    for teacher in teachers:
                        if slot.id in teacher.unavailable_slots:
                            continue
                        if (teacher.id, slot.id, freq) in teacher_busy or (teacher.id, slot.id, WeekFrequency.WEEKLY) in teacher_busy:
                            continue

                        # Ищем комнату
                        for room in rooms:
                            if room.capacity < st_count:
                                continue
                            if not set(req_feats).issubset(set(room.features)):
                                continue
                            if (room.id, slot.id, freq) in room_busy or (room.id, slot.id, WeekFrequency.WEEKLY) in room_busy:
                                continue

                            assigned_slot = slot
                            assigned_teacher = teacher
                            assigned_room = room
                            break

                        if assigned_room:
                            break

                    if assigned_room:
                        break

                if assigned_slot and assigned_room and assigned_teacher:
                    # Фиксируем в эталоне
                    for sub in target_subs:
                        group_busy.add((sub, assigned_slot.id, freq))
                    teacher_busy.add((assigned_teacher.id, assigned_slot.id, freq))
                    room_busy.add((assigned_room.id, assigned_slot.id, freq))

                    lesson_id = f"L_{lesson_counter:03d}"
                    ground_truth[lesson_id] = (assigned_slot.id, assigned_room.id)

                    is_pinned = (self.rng.random() < pin_ratio)
                    lessons.append(
                        LessonInputDTO(
                            id=lesson_id,
                            subject=f"Дисциплина {l_idx+1}",
                            teacher_id=assigned_teacher.id,
                            teacher_name=assigned_teacher.name,
                            atomic_group_ids=target_subs,
                            student_count=st_count,
                            frequency=freq,
                            required_features=req_feats,
                            pinned=is_pinned,
                            pinned_slot_id=assigned_slot.id if is_pinned else None,
                            pinned_room_id=assigned_room.id if is_pinned else None,
                            pinned_room_name=assigned_room.name if is_pinned else None,
                            start_time=assigned_slot.start_time if is_pinned else None,
                            end_time=assigned_slot.end_time if is_pinned else None,
                        )
                    )
                    lesson_counter += 1

        request = SolveRequest(
            slots=slots,
            rooms=rooms,
            teachers=teachers,
            atomic_groups=groups,
            external_blocks=[],
            lessons=lessons,
            solver_timeout_seconds=20,
            bells=list(DEFAULT_BELLS),
        )
        return request, ground_truth
