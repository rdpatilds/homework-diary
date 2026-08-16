from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassSection:
    """A cohort. Class and section always travel together and are always
    compared, so they are one value with one normalisation rule."""

    class_name: str
    section: str

    @classmethod
    def parse(cls, class_name: str, section: str) -> "ClassSection":
        normalised_class = " ".join(class_name.split()).upper()
        normalised_section = " ".join(section.split()).upper()
        if not normalised_class:
            raise ValueError("Class is required")
        if not normalised_section:
            raise ValueError("Section is required")
        return cls(normalised_class, normalised_section)

    def __str__(self) -> str:
        return f"{self.class_name}-{self.section}"
