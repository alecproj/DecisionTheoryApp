from dataclasses import dataclass, field
from typing import Iterable, Sequence

@dataclass
class MarkdownReporter:
    _parts: list[str] = field(default_factory=list)

    def h1(self, text: str) -> None:
        self._parts.append(f"# {text}\n")

    def h2(self, text: str) -> None:
        self._parts.append(f"## {text}\n")

    def text(self, text: str) -> None:
        self._parts.append(f"{text}\n")

    def table(self, headers: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
        self._parts.append("| " + " | ".join(headers) + " |\n")
        self._parts.append("| " + " | ".join(["---"] * len(headers)) + " |\n")
        for r in rows:
            self._parts.append("| " + " | ".join(map(str, r)) + " |\n")
        self._parts.append("\n")

    def get_markdown(self) -> str:
        return "".join(self._parts).strip() + "\n"
