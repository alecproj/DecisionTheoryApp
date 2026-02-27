import os
import pytest
from pathlib import Path
from app.algorithms.example.schema import validate_input, AHPInput
# Жду пока подтянут backend под класс AHPInput, чтобы тестировать его валидацию на реальных CSV-файлах.

CSV_TEST_DIR = Path(__file__).parent / "csv-test-1-algo"

#Чтение csv с папки csv-test-1-algo
def read_csv_file(filename: str) -> str:
    file_path = CSV_TEST_DIR / filename
    if not file_path.exists():
        pytest.skip(f"Файл {filename} не найден в {CSV_TEST_DIR}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()
    
@pytest.fixture
def valid_3_basic_csv():
    return read_csv_file("valid_3_basic.csv")

@pytest.fixture
def valid_comma_decimals_csv():
    return read_csv_file("valid_comma_decimals.csv")

@pytest.fixture
def valid_max_size():
    return read_csv_file("valid_max_size.csv")

@pytest.fixture
def valid_minimal_csv():
    return read_csv_file("valid_minimal.csv")

@pytest.fixture
def valid_with_dev0_placeholders_csv():
    return read_csv_file("valid_with_dev0_placeholders.csv")

@pytest.fixture
def edge_auto_diagonal_csv():
    return read_csv_file("edge_auto_diagonal.csv")

@pytest.fixture
def edge_auto_inverse_csv():
    return read_csv_file("edge_auto_inverse.csv")

@pytest.fixture
def invalid_just_2_strings_csv():
    return read_csv_file("invalid_just_2_strings.csv")

@pytest.fixture
def invalid_mismatched_sizes_csv():
    return read_csv_file("invalid_mismatched_sizes.csv")

@pytest.fixture
def invalid_no_pairwise_csv():
    return read_csv_file("invalid_no_pairwise.csv")

@pytest.fixture
def invalid_non_numeric_pairwise_csv():
    return read_csv_file("invalid_non_numeric_pairwise.csv")

@pytest.fixture
def invalid_non_numeric_scores_csv():
    return read_csv_file("invalid_non_numeric_scores.csv")

#Директория csv-файлов существует, чтобы тесты делать?
def test_csv_test_directory_exists():
    assert CSV_TEST_DIR.exists(), f"Директория {CSV_TEST_DIR} не найдена"

#Есть ли хотя бы один тест в ней?
def test_csv_files_exist():
    csv_files = list(CSV_TEST_DIR.glob("*.csv"))
    assert len(csv_files) > 0, f"Нет CSV файлов в {CSV_TEST_DIR}"