<p align="center">
  <img
    src="icons/icon.png"
    alt="ok-template logo"
    width="256"
    height="256"
  />
</p>

<h1 align="center">ok-template</h1>

<p>
一个基于图像识别的游戏自动化模板项目，基于 <a href="https://ok-script.com/">ok-script</a> 开发。
<br />
A ready-to-use template for building game automation tools with <a href="https://ok-script.com/">ok-script</a>.
</p>

<p><i>通过模拟 Windows 用户接口进行操作，无内存读取、无文件修改</i></p>

<!-- Badges -->
<div align="center">

![平台](https://img.shields.io/badge/platform-Windows-blue)

</div>

### [English Readme](README_en.md) | 中文说明

---

## 这是什么

本项目是 ok-script 自动化项目的**通用骨架**，已包含：

- 可运行的入口（`main.py` / `main_debug.py`）与 ok-script 配置（`src/config.py`）
- 任务骨架：一次性任务（`src/tasks/onetime`）、触发式任务（`src/tasks/trigger`）、测试任务（`src/tasks/test`）
- 通用基类 `src/core/BaseGameTask.py`：配置迁移、暂停感知的等待/睡眠、异常处理、配置分组
- 全局配置页与账号配置页（`src/gui`）
- 截图、OCR 纠错、叠加层 DPI、计划任务、截图侧车等启动补丁（`src/patches`）
- 6 种语言的 i18n 目录（`i18n/*/LC_MESSAGES/ok.po`）与 OCR 语言 JSON（`assets/lang`）
- 单元测试（`tests`）、通用脚本（`scripts`、`tools`）、GitHub Actions CI（`.github/workflows`）
- mkdocs 文档骨架（`docs`）与发布脚本（`auto_release.py`）

使用时只需把游戏相关的窗口配置、任务、模板资源（`ok_templates` 等）替换/补充进来即可。

## 从源码运行 (Python)

本项目仅支持 Python 3.12 版本，必须以管理员权限启动 CMD、PyCharm、VSCode。依赖管理使用 [uv](https://docs.astral.sh/uv/)（需先安装 uv）。

```bash
# 创建虚拟环境并安装/更新依赖
uv sync

# 运行 Release 版本
uv run python main.py

# 运行 Debug 版本
uv run python main_debug.py
```

## 命令行参数

您可以通过命令行参数实现自动化启动。

```pwsh
# 启动后自动执行第1个任务，并在任务完成后退出程序
ok-template.exe -t 1 -e
```

- `-t` 或 `--task`: 启动后自动执行第N个任务（`src/config.py` 中 `onetime_tasks` 列表的序号，也支持任务名）。
- `-e` 或 `--exit`: 任务执行完毕后自动退出程序。

## 开发调试与测试

```bash
# 执行 tests/ 下全部测试脚本（PowerShell）
./run_tests.ps1

# 或逐个运行 unittest
python -m unittest tests/TestConfig.py
```

若你在开发“识别类任务”（OCR/模板/颜色识别），建议优先在 `main_debug.py` 下调试，配合日志与截图目录排查。

## 文档

- 从源码运行：[docs/dev/QUICKSTART.md](docs/dev/QUICKSTART.md)
- 开发指南：[docs/dev/DEVELOPMENT.md](docs/dev/DEVELOPMENT.md)

## ❤️ 致谢

- [ok-oldking/OnnxOCR](https://github.com/ok-oldking/OnnxOCR)
- [zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)