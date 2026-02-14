# DecisionTheoryApp

## Архитектура проекта

```
DecisionTheoryApp/
  app/                      # Flask backend: API + бизнес-логика + алгоритмы
    __init__.py             # Создание Flask-приложения, регистрация blueprints, инициализация Mongo

    api/                    # HTTP API (JSON), с которым работает фронтенд
      algorithms.py         # список доступных алгоритмов
      runs.py               # запуск алгоритма с входными данными
      reports.py            # получение отчётов по запуску

    services/               # Слой бизнес-логики (не HTTP и не алгоритмы)
      run_service.py        # Логика запуска: валидация → выполнение → сохранение run и report

    algorithms/             # Реализации алгоритмов теории принятия решений
      registry.py           # Реестр алгоритмов (что доступно и как к ним обратиться)

      example/              # Пример одного алгоритма (шаблон для новых)
        schema.py           # Описание входных данных алгоритма (поля, типы, валидация)
        algo.py             # Реализация алгоритма; пишет отчёт через reporter

    reporting/              # Генерация и форматирование отчётов
      reporter.py           # Reporter: собирает отчёт (Markdown) единым образом

    db/                     # Работа с базой данных
      mongo.py              # Подключение к MongoDB и получение коллекций

  frontend/                 # Статичный фронтенд (локально и для GitHub Pages)
    src/                    # Исходники фронта
      index.html            # Страница выбора алгоритма
      input.html            # Страница ввода входных данных
      report.html           # Страница просмотра отчёта
      app.js                # Логика фронта: API-запросы или работа с моками
      style.css             # Стили интерфейса

    mocks/                  # Мок-данные для демо (GitHub Pages, без backend)
      algorithms.json       # Мок списка алгоритмов
      run_created.json      # Мок ответа запуска алгоритма
      report.json           # Мок отчёта

    build/                  # Собранная версия фронта (публикуется на Pages)

  docs/                     # Документация проекта (как запускать, как добавлять алгоритмы)

  tests/                    # Автотесты
    test_algorithms.py      # Тесты алгоритмов (input → отчёт)
    test_routes.py          # Тесты API роутов Flask

  docker/                   # Контейнеризация и локальный запуск
    docker-compose.yml      # Поднимает backend + MongoDB
    Dockerfile              # Сборка Docker-образа backend

  .github/workflows/        # CI/CD
    ci.yml                  # Проверки: тесты, линтеры (на PR и main)
    pages.yml               # Публикация фронта (frontend/build) на GitHub Pages
```

## Запуск backend

0. Установить docker, docker-compose.

1. Из корня проекта:

```sh
docker compose -f docker/docker-compose.yml up --build
```

2. Проверить health:

```sh
curl http://localhost:8000/health
```

3. Список алгоритмов:

```sh
curl http://localhost:8000/api/algorithms
```

4. Запуск example:

```sh
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"algorithm_id":"example","input":{"a":2,"b":3}}'
```

5. Получить отчёт (подставь run_id):

```sh
curl http://localhost:8000/api/reports/<RUN_ID>
```

## Запуск frontend

1. Собери build папку вручную:


```sh
rm -rf frontend/build
mkdir -p frontend/build/mocks
cp -r frontend/src/* frontend/build/
cp -r frontend/mocks/* frontend/build/mocks/
```

2. Запусти сервер:

```sh
python -m http.server 5173 --directory frontend/build
```

3. Открывай:

```sh
http://localhost:5173/
```

## Запуск тестов

1. Поднять только Mongo:

```sh
docker compose -f docker/docker-compose.yml up -d mongo
```


2. Установить dev зависимости:

```sh
pip install -e ".[dev]"
```

3. Запустить тесты:

```sh
pytest
```

