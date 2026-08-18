<p align="center">
  <img
    src="icons/icon.png"
    alt="ok-ap logo"
    width="256"
    height="256"
  />
</p>

<h1 align="center">ok-ap</h1>

<p>
Game automation tool for Azur Promilia, built with <a href="https://ok-script.com/">ok-script</a>.
<br />
Image-recognition-based automation, developed with <a href="https://ok-script.com/">ok-script</a>.
</p>

<p><i>Operates by simulating Windows user input. No memory reading, no file modification.</i></p>

<!-- Badges -->
<div align="center">

![Platform](https://img.shields.io/badge/platform-Windows-blue)

</div>

### [中文说明](README.md) | English Readme

---

## What is this

This repository is an ok-script automation project for **Azur Promilia** (蓝色星原：旅谣). It already includes:

- Runnable entry points (`main.py` / `main_debug.py`) and the ok-script app config (`src/config.py`)
- Task skeletons: one-time tasks (`src/tasks/onetime`), trigger tasks (`src/tasks/trigger`), test tasks (`src/tasks/test`)
- Generic base class `src/core/BaseGameTask.py`: config migration, pause-aware sleep/wait, exception handling, config groups
- Global config tab and per-account config tab (`src/gui`)
- Startup patches for screenshots, OCR text fixing, overlay DPI, Windows Task Scheduler, screenshot sidecars, etc. (`src/patches`)
- 6-locale i18n directories (`i18n/*/LC_MESSAGES/ok.po`) and OCR language JSON (`assets/lang`)
- Unit tests (`tests`), generic scripts (`scripts`, `tools`), GitHub Actions CI (`.github/workflows`)
- mkdocs documentation skeleton (`docs`) and release scripts (`auto_release.py`)

To use it, replace the game window config, tasks, and template assets (e.g. `ok_templates`) with your own.

## Run from source (Python)

Python **3.12 only**. Run CMD, PyCharm, or VSCode as **Administrator**. Dependencies are managed with [uv](https://docs.astral.sh/uv/) (install uv first).

```bash
# Create the virtual environment and install/update dependencies
uv sync

# Run Release version
uv run python main.py

# Run Debug version
uv run python main_debug.py
```

## Command-line arguments

```powershell
# Auto-run the 1st task and exit upon completion
ok-ap.exe -t 1 -e
```

- `-t` or `--task`: run the Nth task (index in the `onetime_tasks` list of `src/config.py`, or a task name).
- `-e` or `--exit`: exit automatically after the task completes.

## Development & tests

```bash
# Run all scripts under tests/ (PowerShell)
./run_tests.ps1

# Or run unittest case-by-case
python -m unittest tests/TestConfig.py
```

## Documentation

- Run from source: [docs/dev/QUICKSTART.md](docs/dev/QUICKSTART.md)
- Development guide: [docs/dev/DEVELOPMENT.md](docs/dev/DEVELOPMENT.md)

## Acknowledgements

- [ok-oldking/OnnxOCR](https://github.com/ok-oldking/OnnxOCR)
- [zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)