import pytest

from app.classroom import ClassSection


@pytest.mark.parametrize(
    "raw_class, raw_section",
    [("8", "A"), (" 8 ", " a "), ("8", "a"), ("8", "A "), ("  8", "A")],
)
def test_cohort_is_the_same_however_it_is_typed(raw_class: str, raw_section: str):
    assert ClassSection.parse(raw_class, raw_section) == ClassSection("8", "A")


def test_inner_whitespace_collapses():
    assert ClassSection.parse("grade   8", "sec  a") == ClassSection("GRADE 8", "SEC A")


@pytest.mark.parametrize("raw_class, raw_section", [("", "A"), ("  ", "A"), ("8", " ")])
def test_blank_parts_are_rejected(raw_class: str, raw_section: str):
    with pytest.raises(ValueError):
        ClassSection.parse(raw_class, raw_section)


def test_cohorts_with_different_sections_differ():
    assert ClassSection.parse("8", "A") != ClassSection.parse("8", "B")
