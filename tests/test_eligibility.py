from datetime import date, timedelta
from decimal import Decimal

import pytest

from models import StudentProfile, EligibilityRule, Scholarship
from services.eligibility_service import (
    RuleError,
    check_scholarship,
    evaluate_rule,
    scholarship_accepts,
    validate_rule,
)


def profile(**overrides):
    """An in-memory StudentProfile (not saved) for pure rule evaluation."""
    values = dict(
        category="OBC",
        annual_income=Decimal("200000"),
        course="MCA",
        academic_percentage=Decimal("65"),
        state="Maharashtra",
        academic_year="2026-27",
        gender="Female",
        district="Pune",
        college_name="Sample College",
        university_name="Sample University",
    )
    values.update(overrides)
    return StudentProfile(**values)


def rule(key, op, value):
    return EligibilityRule(criteria_key=key, operator=op, criteria_value=value)


def scholarship(rules=(), active=True, start=None, end=None):
    s = Scholarship(name="S", is_active=active,
                    application_start_date=start, application_end_date=end)
    s.eligibility_rules = list(rules)
    return s


# ----- the example from the project brief -------------------------------

def test_brief_example_is_eligible():
    s = scholarship([
        rule("category", "equal", "OBC"),
        rule("course", "equal", "MCA"),
        rule("annual_income", "less_than_equal", "250000"),
        rule("academic_percentage", "greater_than_equal", "50"),
        rule("state", "equal", "Maharashtra"),
    ])
    result = check_scholarship(profile(), s, today=date(2026, 6, 1))
    assert result.eligible
    assert result.reasons == []


def test_income_above_limit_gives_exact_reason():
    s = scholarship([rule("annual_income", "less_than_equal", "150000")])
    result = check_scholarship(profile(), s, today=date(2026, 6, 1))
    assert not result.eligible
    assert result.reasons == [
        "Annual family income is 200,000.00, but the scheme requires it to be "
        "at most 150,000.00."
    ]


# ----- every operator ----------------------------------------------------

@pytest.mark.parametrize("key,op,value,expected", [
    ("category", "equal", "obc", True),          # case-insensitive
    ("category", "equal", "SC", False),
    ("category", "not_equal", "SC", True),
    ("category", "not_equal", "OBC", False),
    ("annual_income", "less_than", "200001", True),
    ("annual_income", "less_than", "200000", False),
    ("annual_income", "less_than_equal", "200000", True),
    ("annual_income", "greater_than", "199999", True),
    ("annual_income", "greater_than", "200000", False),
    ("annual_income", "greater_than_equal", "200000", True),
    ("category", "in", "OBC, SC, ST", True),
    ("category", "in", "SC,ST", False),
    ("category", "not_in", "SC,ST", True),
    ("category", "not_in", "OBC,SC", False),
    ("annual_income", "in", "100000,200000", True),
])
def test_operators(key, op, value, expected):
    result = evaluate_rule(rule(key, op, value), profile())
    assert result.passed is expected


def test_missing_profile_value_fails_with_helpful_message():
    result = evaluate_rule(rule("annual_income", "less_than", "1"),
                           profile(annual_income=None))
    assert not result.passed
    assert "missing from your profile" in result.reason


def test_misconfigured_rule_fails_safely():
    result = evaluate_rule(rule("annual_income", "less_than", "abc"), profile())
    assert not result.passed
    assert "misconfigured" in result.reason


# ----- validation of administrator input -------------------------------

@pytest.mark.parametrize("key,op,value", [
    ("unknown_field", "equal", "x"),
    ("category", "bogus_op", "OBC"),
    ("annual_income", "less_than", "lots"),
    ("category", "less_than", "OBC"),     # ordering on text is rejected
    ("category", "in", " , "),
    ("category", "equal", ""),
])
def test_invalid_rules_are_rejected(key, op, value):
    with pytest.raises(RuleError):
        validate_rule(key, op, value)


def test_valid_rule_passes_validation():
    validate_rule("annual_income", "less_than_equal", "250000")
    validate_rule("category", "in", "OBC,SC")


# ----- scholarship-level conditions --------------------------------------

def test_inactive_scholarship_is_ineligible():
    result = check_scholarship(profile(), scholarship(active=False))
    assert not result.eligible


def test_deadline_passed_is_ineligible():
    s = scholarship(end=date(2026, 1, 31))
    result = check_scholarship(profile(), s, today=date(2026, 2, 1))
    assert not result.eligible
    assert "deadline" in " ".join(result.reasons).lower()


def test_not_yet_open_is_ineligible():
    s = scholarship(start=date(2026, 3, 1))
    result = check_scholarship(profile(), s, today=date(2026, 2, 1))
    assert not result.eligible


def test_no_rules_means_criteria_pass():
    result = check_scholarship(profile(), scholarship(), today=date(2026, 6, 1))
    assert result.eligible


def test_scholarship_accepts_is_used_for_listing_filters():
    s = scholarship([rule("category", "in", "OBC,SC")])
    assert scholarship_accepts(s, "category", "OBC")
    assert not scholarship_accepts(s, "category", "OPEN")
    # No rule on course means every course is accepted.
    assert scholarship_accepts(s, "course", "B.Sc")
