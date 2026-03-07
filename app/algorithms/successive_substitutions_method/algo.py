from app.algorithms.example.schema import ExampleInput

def run(input_data: ExampleInput, reporter) -> None:
    reporter.h1("Example algorithm")
    reporter.text("This is a stub algorithm for test запуск.")
    s = input_data.a + input_data.b
    reporter.h2("Result")
    reporter.table(["a", "b", "a+b"], [[input_data.a, input_data.b, s]])
