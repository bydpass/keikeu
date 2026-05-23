from dataclasses import dataclass, field


@dataclass
class KeikeuSpec:
    raw_idea: str
    tags: list[str] = field(default_factory=list)
    vinegar: list[str] = field(default_factory=list)
    summary: str = ""
    dumplings: list[str] = field(default_factory=list)
    final_form: str = ""
    taboos: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
