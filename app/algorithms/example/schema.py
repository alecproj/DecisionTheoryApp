from dataclasses import dataclass

@dataclass(frozen=True)
class ExampleInput:
    a: float
    b: float

def validate_input(data: dict) -> ExampleInput:
    if "a" not in data or "b" not in data:
        raise ValueError("Input must contain fields: a, b")
    return ExampleInput(a=float(data["a"]), b=float(data["b"]))
