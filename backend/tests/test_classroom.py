import pytest

from app.classroom import ClassSection, StudentKey


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


@pytest.mark.parametrize("raw_roll", ["24", " 24 ", "24  "])
def test_a_student_is_the_same_however_the_roll_is_typed(raw_roll: str):
    assert StudentKey.parse("8", "a", raw_roll) == StudentKey.parse("8", "A", "24")


def test_letters_in_a_roll_are_normalised():
    assert StudentKey.parse("8", "A", "b12").roll_no == "B12"


def test_the_same_roll_in_another_cohort_is_another_student():
    assert StudentKey.parse("8", "A", "24") != StudentKey.parse("8", "B", "24")


@pytest.mark.parametrize("raw_roll", ["", "   "])
def test_a_blank_roll_is_rejected(raw_roll: str):
    with pytest.raises(ValueError):
        StudentKey.parse("8", "A", raw_roll)


def test_leading_zeros_are_a_different_student():
    """Deliberate. Merging 07 into 7 would let one student see another's
    submissions if a school ever used both."""
    assert StudentKey.parse("8", "A", "07") != StudentKey.parse("8", "A", "7")
