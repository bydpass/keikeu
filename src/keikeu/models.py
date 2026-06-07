from dataclasses import dataclass, field


@dataclass
class Memo:
    raw: str


@dataclass
class Ticket:
    raw: str
    tags: list[str] = field(default_factory=list)
    jiaozi_cu: list[str] = field(default_factory=list)
    summary: str = ""
    jiaozi: list[str] = field(default_factory=list)
    product: str = ""
    taboo: list[str] = field(default_factory=list)
    next_step: list[str] = field(default_factory=list)
