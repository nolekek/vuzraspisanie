import json
import os
import re
import ssl
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from app.api.schemas import (
    AtomicGroupDTO,
    BaseSlotDTO,
    LessonInputDTO,
    RoomDTO,
    SolveRequest,
    TeacherDTO,
    SLOT_BELLS,
    TIME_SLOT_MAP,
    DEFAULT_BELLS,
)
from app.domain.enums import DayOfWeek, WeekFrequency


RUS_DAY_MAP = {
    "пн": DayOfWeek.MONDAY,
    "вт": DayOfWeek.TUESDAY,
    "ср": DayOfWeek.WEDNESDAY,
    "чт": DayOfWeek.THURSDAY,
    "пт": DayOfWeek.FRIDAY,
    "сб": DayOfWeek.SATURDAY,
}


class USPUParser:
    """Парсер реального расписания УрГПУ (uspu.ru) и конвертер в формат SolveRequest."""

    AJAX_URL = "https://uspu.ru/ajax/rasp.php"

    def __init__(self):
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def fetch_group_html(self, group_name: str) -> str:
        data = urllib.parse.urlencode({"group_name": group_name}).encode("utf-8")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://uspu.ru/education/eios/schedule/",
            "X-Requested-With": "XMLHttpRequest",
        }
        req = urllib.request.Request(self.AJAX_URL, data=data, headers=headers)
        with urllib.request.urlopen(req, context=self.ctx, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    def parse_time_to_slot(self, time_str: str) -> int:
        norm_time = time_str.replace(".", ":").strip()
        start_time = norm_time.split("-")[0].strip()
        for known_time, slot_num in TIME_SLOT_MAP.items():
            if known_time in start_time:
                return slot_num
        return 1

    def parse_groups(
        self,
        group_names: List[str] = ["АИ-2431", "АИ-2331"],
        pin_ratio: float = 0.15,
    ) -> SolveRequest:
        rooms_dict: Dict[str, RoomDTO] = {}
        teachers_dict: Dict[str, TeacherDTO] = {}
        atomic_groups_dict: Dict[str, AtomicGroupDTO] = {}
        lessons: List[LessonInputDTO] = []
        pinned_occupied_keys = set()

        all_base_slots: Dict[str, BaseSlotDTO] = {}
        for day in DayOfWeek:
            for s in range(1, 8):
                slot_id = f"{day.value[:3]}_{s}"
                bell = SLOT_BELLS.get(s, ("08:30", "10:00"))
                all_base_slots[slot_id] = BaseSlotDTO(
                    id=slot_id,
                    day_of_week=day,
                    slot_number=s,
                    start_time=bell[0],
                    end_time=bell[1],
                )

        lesson_id_counter = 1

        for grp in group_names:
            # Создаем атомарную группу
            grp_clean = grp.strip()
            sub1_id = f"{grp_clean}_SUB1"
            sub2_id = f"{grp_clean}_SUB2"
            atomic_groups_dict[sub1_id] = AtomicGroupDTO(
                id=sub1_id,
                name=f"{grp_clean} (Подгр. 1)",
                parent_group=grp_clean,
                student_count=15,
            )
            atomic_groups_dict[sub2_id] = AtomicGroupDTO(
                id=sub2_id,
                name=f"{grp_clean} (Подгр. 2)",
                parent_group=grp_clean,
                student_count=15,
            )

            html = self.fetch_group_html(grp)
            soup = BeautifulSoup(html, "html.parser")
            day_items = soup.find_all("div", class_="rasp-item")

            # Группируем календарные дни по учебным неделям (новая неделя начинается с Пн)
            weeks: List[List] = []
            curr_wk: List = []
            for d in day_items:
                w_el = d.find("div", class_="rasp-week")
                if not w_el:
                    continue
                day_short = w_el.text.strip().lower()
                if day_short == "пн" and curr_wk:
                    weeks.append(curr_wk)
                    curr_wk = []
                curr_wk.append(d)
            if curr_wk:
                weeks.append(curr_wk)

            # Выбираем ровно 2 учебные недели для формирования цикла (Числитель / Знаменатель)
            full_weeks = [w for w in weeks if len(w) >= 4]
            if len(full_weeks) >= 2:
                selected_weeks = [
                    (full_weeks[0], WeekFrequency.NUMERATOR),
                    (full_weeks[1], WeekFrequency.DENOMINATOR),
                ]
            elif len(weeks) >= 2:
                selected_weeks = [
                    (weeks[0], WeekFrequency.NUMERATOR),
                    (weeks[1], WeekFrequency.DENOMINATOR),
                ]
            elif len(weeks) == 1:
                selected_weeks = [(weeks[0], WeekFrequency.WEEKLY)]
            else:
                selected_weeks = []

            for week_days, frequency in selected_weeks:
                for d in week_days:
                    week_day_el = d.find("div", class_="rasp-week")
                    if not week_day_el:
                        continue
                    day_short = week_day_el.text.strip().lower()
                    dow = RUS_DAY_MAP.get(day_short, DayOfWeek.MONDAY)

                    paras = d.find_all("div", class_="rasp-para")
                    for p in paras:
                        time_span = p.find("span", class_="para-time")
                        time_text = time_span.text.strip() if time_span else "08:30 - 10:00"
                        slot_num = self.parse_time_to_slot(time_text)
                        slot_id = f"{dow.value[:3]}_{slot_num}"
                        bell = SLOT_BELLS.get(slot_num, ("08:30", "10:00"))

                        desc = p.find("div", class_="rasp-desc")
                        if not desc:
                            continue
                        lines = [l.strip() for l in desc.stripped_strings]
                        if not lines:
                            continue

                        subject = lines[0]
                        room_name = (
                            lines[1]
                            if len(lines) > 1
                            and not lines[1].startswith("Преподаватель")
                            else "Аудитория 101"
                        )
                        teacher_name = "Преподаватель Кафедры"
                        for line in lines:
                            if line.startswith("Преподаватель:"):
                                teacher_name = line.replace("Преподаватель:", "").strip()
                                break

                        # Санитизация ID
                        teacher_id = "T_" + re.sub(
                            r"[^a-zA-Z0-9а-яА-Я_]", "_", teacher_name
                        )[:20]
                        room_id = "R_" + re.sub(r"[^a-zA-Z0-9а-яА-Я_]", "_", room_name)[
                            :20
                        ]

                        # Определение оборудования
                        req_features = []
                        if (
                            "компьютер" in room_name.lower()
                            or "информатик" in subject.lower()
                        ):
                            req_features.append("COMPUTERS")
                        if (
                            "проектор" in room_name.lower()
                            or "лекция" in subject.lower()
                            or "лек" in subject.lower()
                        ):
                            req_features.append("PROJECTOR")
                        if (
                            "физкульт" in room_name.lower()
                            or "спорт" in subject.lower()
                        ):
                            req_features.append("SPORT")

                        # Добавляем преподавателя
                        if teacher_id not in teachers_dict:
                            teachers_dict[teacher_id] = TeacherDTO(
                                id=teacher_id,
                                name=teacher_name,
                                unavailable_slots=[],
                                preferred_slots=[],
                                unwanted_slots=[],
                            )

                        # Добавляем аудиторию
                        if room_id not in rooms_dict:
                            cap = (
                                30
                                if "лаб" in subject.lower()
                                else (100 if "лек" in subject.lower() else 40)
                            )
                            rooms_dict[room_id] = RoomDTO(
                                id=room_id,
                                name=room_name,
                                capacity=cap,
                                features=list(set(req_features + ["PROJECTOR"])),
                            )

                        # Подгруппа или поток
                        is_lab = (
                            "лаб" in subject.lower()
                            or "практикум" in subject.lower()
                            or "подгр" in subject.lower()
                        )
                        assigned_subgroups = (
                            [sub1_id] if is_lab else [sub1_id, sub2_id]
                        )
                        st_count = 15 if is_lab else 30

                        # Валидация пининга (не допускаем фиксации взаимоисключающих пар)
                        is_pinned = False
                        if pin_ratio > 0.0:
                            target_step = int(1.0 / max(pin_ratio, 0.01))
                            if (lesson_id_counter % target_step) == 0:
                                check_keys = [
                                    (slot_id, frequency.value, f"R:{room_id}"),
                                    (slot_id, frequency.value, f"T:{teacher_id}"),
                                ] + [(slot_id, frequency.value, f"G:{gid}") for gid in assigned_subgroups]

                                if not any(k in pinned_occupied_keys for k in check_keys):
                                    is_pinned = True
                                    for k in check_keys:
                                        pinned_occupied_keys.add(k)

                        lesson = LessonInputDTO(
                            id=f"USPU_L_{lesson_id_counter:03d}",
                            subject=subject,
                            teacher_id=teacher_id,
                            teacher_name=teacher_name,
                            atomic_group_ids=assigned_subgroups,
                            student_count=st_count,
                            frequency=frequency,
                            required_features=req_features,
                            pinned=is_pinned,
                            pinned_slot_id=slot_id if is_pinned else None,
                            pinned_room_id=room_id if is_pinned else None,
                            pinned_room_name=room_name if is_pinned else None,
                            start_time=bell[0] if is_pinned else None,
                            end_time=bell[1] if is_pinned else None,
                        )
                        lessons.append(lesson)
                        lesson_id_counter += 1

        return SolveRequest(
            slots=list(all_base_slots.values()),
            rooms=list(rooms_dict.values()),
            teachers=list(teachers_dict.values()),
            atomic_groups=list(atomic_groups_dict.values()),
            external_blocks=[],
            lessons=lessons,
            solver_timeout_seconds=20,
            bells=list(DEFAULT_BELLS),
        )


uspu_parser = USPUParser()
