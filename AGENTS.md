# AGENTS.md

项目级强制规则。每次会话开始必须读取并遵守。

## 运行环境

- Python：依赖通过 [uv](https://docs.astral.sh/uv/) 管理，`uv sync` 创建仓库本地 `.venv`，用 `uv run python ...` 执行（见 `.agents/skills/use-local-venv`）。`pyproject.toml` + `uv.lock` 为唯一来源，`requirements.txt` 为发布流水线的派生产物，勿手改。
- 测试：`run_tests.ps1`（经 `uv run`）或 `uv run python -m unittest discover -s tests`。
- 日志：`logs/ok-script.log`（配置历史、任务执行、OCR 均可在此排查）；历史日志位于同目录的 `ok-script.YYYY-MM-DD.log` 文件中。

## 代码风格

- 任务类基于 ok-script：`BaseTask` / `TriggerTask`，本项目通用基类为 `src/core/BaseGameTask.py`。见 `.agents/skills/ok-script-tasks`。
- 任务字符串国际化见 `.agents/skills/ok-script-i18n`（用 `task_i18n_helper.py compile --i18n i18n` 编译 `.mo`）。
- 生成任务代码见 `.agents/skills/ok-script-codegen`。
- 新增任务后必须在 `src/config.py` 的 `onetime_tasks` / `trigger_tasks` 中注册。

## 配置键名修改（重要）

`configs/` 目录下的 JSON 是用户运行数据，修改 `default_config` 中的配置键名时必须遵守以下顺序，否则会丢失用户配置：

1. **先加迁移表，再改键名**：在同一个任务类中先添加 `config_key_migrations = {旧键: 新键}`，再修改 `default_config` / 键名常量 / 键生成函数。二者必须在同一提交中完成，禁止分步部署。
2. **迁移表生效前禁止运行程序**：改完键名后不要直接启动应用验证；先用 `migrate_config_file_keys(<任务名>, migrations)`（见 `src/core/config_migration.py`）跑迁移测试，确认旧值已复制到新键。
3. **同步 i18n**：键名变化后必须同步全部 `i18n/*/LC_MESSAGES/ok.po` 的 msgid（msgid 必须与代码键名一致），并用 `task_i18n_helper.py compile` 编译 `.mo`。
4. **同步文档**：搜索 `docs/` 中出现的旧键名并更新。
5. **配置丢失可恢复**：`logs/ok-script.log` 中每行 `Config:init self.config = {...}` 保存了完整历史配置（DEBUG 级别），可从最后一次出现旧键名的记录恢复用户值。

## lang JSON key 命名约定（重要）

`assets/lang/` 下的语言 JSON 中：

- **新增 key 用语义化命名**，不要沿用旧的 `k_<md5前8位>` hash 风格。
- 每个 key 下为 6 种语言节点（`zh_CN`/`zh_TW`/`en_US`/`ja_JP`/`ko_KR`/`es_ES`），格式 `{"string": "..."}` 或 `{"pattern": "..."}`。
- 代码通过 `self.lang.<模块名>.<语义化key>` 读取，自动按当前 UI 语言选择（见 `src/data/lang/`）。
- **lang JSON 只放 OCR 匹配文本**。UI 说明（如 `instructions` 富文本）**不用 lang JSON**，改用 `self.tr("中文msgid")` 走 ok 的 gettext i18n：msgid 写入 `i18n/*/LC_MESSAGES/ok.po`（msgid 必须与代码字符串逐字一致，含全角标点/`{占位符}`），再用 `task_i18n_helper.py compile` 编译 `ok.mo` 生效。
- **最小原则**：emoji、`└─`/`├─`、HTML 标签/颜色等无需翻译的内容一律留在代码里拼，只把需翻译的纯文本放进 i18n 数据。