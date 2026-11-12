from enum import Enum


class DayOfWeek(Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"

    @property
    def index(self) -> int:
        mapping = {
            DayOfWeek.MONDAY: 1,
            DayOfWeek.TUESDAY: 2,
            DayOfWeek.WEDNESDAY: 3,
            DayOfWeek.THURSDAY: 4,
            DayOfWeek.FRIDAY: 5,
            DayOfWeek.SATURDAY: 6,
        }
        return mapping[self]


class WeekFrequency(Enum):
    WEEKLY = "WEEKLY"
    NUMERATOR = "NUMERATOR"      # Числитель
    DENOMINATOR = "DENOMINATOR"  # Знаменатель


def overlaps_week(freq1: WeekFrequency, freq2: WeekFrequency) -> bool:
    """Две пары пересекаются по неделям, если хотя бы одна WEEKLY,

    либо их четность строго совпадает.
    """
    if freq1 == WeekFrequency.WEEKLY or freq2 == WeekFrequency.WEEKLY:
        return True
    return freq1 == freq2


class TargetType(Enum):
    TEACHER = "TEACHER"
    ATOMIC_GROUP = "ATOMIC_GROUP"
