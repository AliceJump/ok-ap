# 开发指南（DEVELOPMENT）

## 架构

本项目基于 ok-script。应用配置集中在 `src/config.py`，任务与 Tab 均在此注册。

### 目录职责

| 目录 | 职责 |
|------|------|
| `src/config.py` | ok-script 应用配置：窗口、OCR、模板匹配、任务注册 |
| `src/core/BaseGameTask.py` | 任务基类：配置迁移、暂停感知计时、异常处理、配置分组 |
| `src/core/config_migration.py` | 配置键迁移工具（改键名时使用，防丢用户配置） |
| `src/core/global_config_store.py` | 全局配置（跨任务共享的 ConfigOption） |
| `src/gui/` | 自定义 Tab：全局配置页、账号配置页 |
| `src/tasks/` | 一次性 / 触发式 / 测试 / 账号存储 |
| `src/interaction/` | 游戏窗口交互与键鼠封装 |
| `src/patches/` | 启动补丁（截图、OCR 纠错、叠加层 DPI 等） |
| `src/data/lang/` | `assets/lang/*.json` 的读取器 |
| `assets/lang/` | OCR 匹配文本（6 语言节点） |
| `i18n/` | gettext 目录（UI 字符串翻译） |

## 配置键迁移

修改 `default_config` 键名时必须先添加迁移表（同一提交完成）：

```python
class MyTask(BaseGameTask):
    config_key_migrations = {"旧键": "新键"}
```

`BaseGameTask.load_config` 会沿 MRO 收集所有迁移表并执行，详见 `src/core/config_migration.py`。

## i18n

- **UI 字符串**：代码用 `self.tr("中文")`，msgid 写入 `i18n/*/LC_MESSAGES/ok.po`，再编译 `.mo`：
  ```bash
  .\.venv\Scripts\python.exe .agent\skills\ok-script-i18n\scripts\task_i18n_helper.py compile --i18n i18n
  ```
- **OCR 匹配文本**：放进 `assets/lang/<模块>.json`，每 key 下 6 种语言节点，代码用 `self.lang.<模块>.<key>` 读取。

## 测试

- 测试位于 `tests/`，使用 `unittest`。
- `run_tests.ps1` 逐个运行；CI（`.github/workflows/build.yml`）在打 tag 时运行。

## 发布

- 本地打 tag：`.\auto_release.ps1 -DryRun`（预览）或直接执行。
- 每日自动发版：`.github/workflows/auto-release.yml` 检查 `deploy.txt` 关注路径是否有变更，有则自动递增版本号并打 tag。
- 打 tag 后 `.github/workflows/build.yml` 自动测试、用 pyappify 打包并发布 Release。

## 目录约定

- 新增任务类必须注册进 `src/config.py`，否则 UI 中不可见。
- 任务/配置相关文档与代码同步更新。