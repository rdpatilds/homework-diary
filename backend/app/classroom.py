from dataclasses import dataclass


def _tidy(raw: str) -> str:
    return " ".join(raw.split()).upper()


@dataclass(frozen=True, slots=True)
class ClassSection:
    """A cohort. Class and section always travel together and are always
    compared, so they are one value with one normalisation rule."""

    class_name: str
    section: str

    @classmethod
    def parse(cls, class_name: str, section: str) -> "ClassSection":
        normalised_class = _tidy(class_name)
        normalised_section = _tidy(section)
        if not normalised_class:
            raise ValueError("Class is required")
        if not normalised_section:
            raise ValueError("Section is required")
        return cls(normalised_class, normalised_section)

    def __str__(self) -> str:
        return f"{self.class_name}-{self.section}"


@dataclass(frozen=True, slots=True)
class StudentKey:
    """Who a submission belongs to. Roll numbers repeat across cohorts, so the
    cohort is part of the identity. Building one is the only way to reach a
    normalised roll number, so no query can be handed a raw string."""

    cohort: ClassSection
    roll_no: str

    @classmethod
    def parse(cls, class_name: str, section: str, roll_no: str) -> "StudentKey":
        normalised_roll = _tidy(roll_no)
        if not normalised_roll:
            raise ValueError("Roll number is required")
        return cls(ClassSection.parse(class_name, section), normalised_roll)

    def __str__(self) -> str:
        return f"{self.cohort} roll {self.roll_no}"
