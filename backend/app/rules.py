"""Deterministic dose rules. No database, no network: everything here is unit-tested.

"Rules decide": every flag a patient or provider sees comes from these functions,
never from the language model.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

# A lift within +/- 30 min of the scheduled time is on time.
ON_TIME_WINDOW = timedelta(minutes=30)
# A lift can be matched to a dose up to 2 h before it is due (counted as early) ...
EARLY_LIMIT = timedelta(hours=2)
# ... or up to 3 h after (counted as late). After that the dose is missed.
MISSED_AFTER = timedelta(hours=3)
# Different drops scheduled at the same time are spaced this far apart,
# because drops need a few minutes between them.
MIN_GAP = timedelta(minutes=5)


@dataclass(frozen=True)
class Step:
    """One schedule step: a drop's daily times over a date range (inclusive)."""

    schedule_id: int
    start_date: date
    end_date: date
    dose_times: tuple[time, ...]


@dataclass(frozen=True)
class PendingDose:
    id: int
    scheduled_at: datetime


def planned_doses(steps: list[Step], day: date, tz: tzinfo, min_gap: timedelta = MIN_GAP) -> list[tuple[int, datetime]]:
    """All (schedule_id, scheduled_at) slots for one local day.

    When several drops share a time, they are staggered by `min_gap` in
    schedule_id order, e.g. 08:00, 08:05, 08:10.
    """
    by_time: dict[time, set[int]] = {}
    for step in steps:
        if step.start_date <= day <= step.end_date:
            for t in step.dose_times:
                by_time.setdefault(t, set()).add(step.schedule_id)

    slots = []
    for t in sorted(by_time):
        base = datetime.combine(day, t, tzinfo=tz)
        for i, schedule_id in enumerate(sorted(by_time[t])):
            slots.append((schedule_id, base + i * min_gap))
    return slots


def classify_lift(scheduled_at: datetime, lifted_at: datetime) -> str:
    """Flag for a lift that was matched to a scheduled dose."""
    delta = lifted_at - scheduled_at
    if abs(delta) <= ON_TIME_WINDOW:
        return "on_time"
    return "early" if delta < timedelta(0) else "late"


def choose_dose(pending: list[PendingDose], lifted_at: datetime) -> PendingDose | None:
    """Pick which pending dose a bottle lift belongs to.

    1. The oldest dose that is already due and not yet missed (a late dose is
       more likely than a very early one).
    2. Otherwise the soonest upcoming dose within EARLY_LIMIT.
    3. Otherwise None: the lift is flagged too_frequent.
    """
    overdue = [d for d in pending if d.scheduled_at <= lifted_at < d.scheduled_at + MISSED_AFTER]
    if overdue:
        return min(overdue, key=lambda d: d.scheduled_at)
    upcoming = [d for d in pending if lifted_at < d.scheduled_at <= lifted_at + EARLY_LIMIT]
    if upcoming:
        return min(upcoming, key=lambda d: d.scheduled_at)
    return None


def is_due(scheduled_at: datetime, now: datetime) -> bool:
    """A pending dose is due (dock alarms) from its time until it becomes missed."""
    return scheduled_at <= now < scheduled_at + MISSED_AFTER


def is_missed(scheduled_at: datetime, now: datetime) -> bool:
    return now >= scheduled_at + MISSED_AFTER
