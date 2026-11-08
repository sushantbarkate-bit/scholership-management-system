"""Configurable eligibility engine.

Rules are stored in the eligibility_rules table (administrators create them
from the UI). This module only interprets them, so no scholarship-specific
condition is hardcoded in Python.

Results are PRELIMINARY: they describe whether a student's recorded data
matches the configured rules. They are not an official approval.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from services.constants import ELIGIBILITY_FIELDS, OPERATORS


class RuleError(ValueError):
    """Raised when an eligibility rule is malformed."""


@dataclass
class Check:
    label: str
    passed: bool
    reason: str


@dataclass
class EligibilityResult:
    checks: list = field(default_factory=list)

    @property
    def eligible(self):
        return all(check.passed for check in self.checks)

    @property
    def reasons(self):
        return [check.reason for check in self.checks if not check.passed]


def _split_list(raw):
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def parse_value(raw, kind, operator):
    """Convert a stored rule value into a comparable Python value.

    Raises RuleError if the value does not suit the field or operator.
    """
    if raw is None or str(raw).strip() == "":
        raise RuleError("A value is required.")

    if OPERATORS[operator][2]:
        items = _split_list(raw)
        if not items:
            raise RuleError("Provide at least one value in the list.")
        if kind == "number":
            try:
                return [Decimal(item) for item in items]
            except InvalidOperation:
                raise RuleError("All list values must be numbers.")
        return [item.lower() for item in items]

    if kind == "number":
        try:
            return Decimal(str(raw).strip())
        except InvalidOperation:
            raise RuleError("The value must be a number.")
    return str(raw).strip().lower()


def validate_rule(criteria_key, operator, raw_value):
    """Validate a rule before it is saved. Raises RuleError on problems."""
    if criteria_key not in ELIGIBILITY_FIELDS:
        raise RuleError("Unknown eligibility criterion.")
    if operator not in OPERATORS:
        raise RuleError("Unknown operator.")

    _, kind, _ = ELIGIBILITY_FIELDS[criteria_key]
    if kind == "text" and operator in ("less_than", "less_than_equal",
                                       "greater_than", "greater_than_equal"):
        raise RuleError("Ordering operators apply only to numeric criteria.")

    parse_value(raw_value, kind, operator)


def _compare(actual, operator, expected):
    if operator == "equal":
        return actual == expected
    if operator == "not_equal":
        return actual != expected
    if operator == "less_than":
        return actual < expected
    if operator == "less_than_equal":
        return actual <= expected
    if operator == "greater_than":
        return actual > expected
    if operator == "greater_than_equal":
        return actual >= expected
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    raise RuleError("Unknown operator.")


def _display(value):
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _field_value(profile, criteria_key):
    _, _, attr = ELIGIBILITY_FIELDS[criteria_key]
    if profile is None:
        return None
    return getattr(profile, attr, None)


def evaluate_rule(rule, profile):
    """Evaluate one EligibilityRule against a StudentProfile. Returns a Check."""
    label, kind, _ = ELIGIBILITY_FIELDS.get(
        rule.criteria_key, (rule.criteria_key, "text", None)
    )
    operator_label, phrase, _ = OPERATORS.get(
        rule.operator, (rule.operator, rule.operator, False)
    )

    try:
        expected = parse_value(rule.criteria_value, kind, rule.operator)
    except RuleError as error:
        return Check(label, False, f"Rule is misconfigured: {error}")

    raw_actual = _field_value(profile, rule.criteria_key)
    if raw_actual is None or str(raw_actual).strip() == "":
        return Check(
            label,
            False,
            f"{label} is missing from your profile. Please complete your profile."
        )

    if kind == "number":
        actual = Decimal(str(raw_actual))
    else:
        actual = str(raw_actual).strip().lower()

    passed = _compare(actual, rule.operator, expected)
    shown_expected = rule.criteria_value
    if kind == "number" and not OPERATORS[rule.operator][2]:
        shown_expected = _display(expected)

    if passed:
        return Check(
            label,
            True,
            f"{label}: {_display(actual) if kind == 'number' else raw_actual} "
            f"meets the requirement ({phrase} {shown_expected})."
        )

    return Check(
        label,
        False,
        f"{label} is {_display(actual) if kind == 'number' else raw_actual}, "
        f"but the scheme requires it to be {phrase} {shown_expected}."
    )


def check_scholarship(profile, scholarship, today=None):
    """Full preliminary eligibility check for one scholarship."""
    today = today or date.today()
    result = EligibilityResult()

    result.checks.append(Check(
        "Scholarship status",
        bool(scholarship.is_active),
        "" if scholarship.is_active else "This scholarship is currently closed."
    ))

    start = scholarship.application_start_date
    if start:
        result.checks.append(Check(
            "Application window opens",
            today >= start,
            "" if today >= start
            else f"Applications open on {start:%d %b %Y}."
        ))

    end = scholarship.application_end_date
    if end:
        result.checks.append(Check(
            "Application deadline",
            today <= end,
            "" if today <= end
            else f"The application deadline ({end:%d %b %Y}) has passed."
        ))

    for rule in scholarship.eligibility_rules:
        result.checks.append(evaluate_rule(rule, profile))

    return result


def scholarship_accepts(scholarship, criteria_key, value):
    """Used by listing filters: would this scholarship accept `value` for a
    criterion? True when there is no rule on that criterion."""
    relevant = [r for r in scholarship.eligibility_rules
                if r.criteria_key == criteria_key]
    if not relevant:
        return True

    _, kind, _ = ELIGIBILITY_FIELDS[criteria_key]
    if kind == "number":
        try:
            actual = Decimal(str(value))
        except InvalidOperation:
            return False
    else:
        actual = str(value).strip().lower()

    for rule in relevant:
        expected = parse_value(rule.criteria_value, kind, rule.operator)
        if not _compare(actual, rule.operator, expected):
            return False
    return True
