# Ruble — приложение для управления личными финансами

**Вариант 43.**  Приложение для учёта доходов и расходов на **Python + Kivy + SQLite**.

## Возможности

- Учёт доходов и расходов с категоризацией транзакций
- Постоянные платежи с автоматическими напоминаниями (за 3 дня до срока по умолчанию)
- Финансовые цели с отображением прогресса
- Линейный график доходов и расходов за выбранный период
- Столбчатая диаграмма расходов по категориям
- Защита данных: PIN-код (4 цифры) и шифрование локальной БД (Fernet + PBKDF2)
- Пагинация списков транзакций и постоянных платежей (по 5 записей)

## Требования

- Python 3.10+
- Android

## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <url-репозитория>
cd Ruble
```

### 2. Создание виртуального окружения

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Запуск приложения

```bash
python main.py
```

При первом запуске создайте PIN-код из 4 цифр. При следующих запусках введите PIN для расшифровки базы данных.

### 5. Запуск тестов

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Запуск в Docker

```bash
docker build -t ruble .
docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix ruble
```

> Для графического интерфейса в Docker нужен X-сервер (Linux) или XQuartz (macOS).

## Сборка APK (Android)

Сборка выполняется через **Buildozer** на **Linux** или **WSL** (на Windows напрямую не поддерживается).

### 1. Подготовка (Ubuntu / WSL)

```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config \
  zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

pip install buildozer cython
```

### 2. Сборка debug APK

```bash
cd Ruble
chmod +x build_apk.sh
./build_apk.sh debug
```

Или напрямую:

```bash
buildozer -v android debug
```

Готовый файл появится в папке `bin/`, например:
`bin/ruble-1.0.0-arm64-v8a-debug.apk`

### 3. Release APK (для публикации)

Создайте keystore и укажите пути в `buildozer.spec` (секция `[android]`), затем:

```bash
./build_apk.sh release
```

### Файлы сборки

| Файл | Назначение |
|------|------------|
| `buildozer.spec` | Конфигурация Buildozer (зависимости, API, разрешения) |
| `build_apk.sh` | Скрипт сборки debug/release/clean |

## Структура проекта

```
Ruble/
├── main.py              # Точка входа, экраны и формы
├── models.py            # SQLAlchemy-модели и бизнес-логика
├── crypto_utils.py      # Шифрование локальной БД
├── charts.py            # Диаграммы (matplotlib)
├── views/               # Kivy KV-разметка
│   ├── auth.kv          # Регистрация PIN
│   ├── login.kv         # Вход
│   ├── main.kv          # Главный экран
│   └── css.kv           # Стили
├── tests/               # Unit-тесты
├── requirements.txt
├── buildozer.spec       # Конфигурация сборки APK
├── build_apk.sh         # Скрипт сборки Android
├── Dockerfile
└── .github/workflows/   # CI/CD
```

## Файлы данных (создаются автоматически)

| Файл | Описание |
|------|----------|
| `config.json` | Хэш PIN-кода |
| `finance.db.enc` | Зашифрованная база SQLite |

> Файлы `finance.db`, `config.json` и `finance.db.enc` добавлены в `.gitignore` и не попадают в репозиторий.

## CI/CD

При push/PR в ветки `main`/`master` GitHub Actions выполняет:

1. Установку зависимостей
2. Проверку импортов модулей
3. Запуск unit-тестов

## Технологии

- **Python** — основной язык
- **Kivy** — кроссплатформенный GUI
- **SQLAlchemy + SQLite** — хранение данных
- **Cryptography** — шифрование БД
- **Matplotlib** — визуализация
- **Docker** — контейнеризация
- **GitHub Actions** — CI/CD

## Лицензия

См. файл [LICENSE](LICENSE).
