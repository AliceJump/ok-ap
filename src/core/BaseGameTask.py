import time
from datetime import datetime

# 覆写框架截图时间戳格式：日期_时分秒（无毫秒）
import ok.gui.debug.Screenshot as _ok_screenshot
from ok import BaseTask, TaskDisabledException, TriggerTask, WaitFailedException

from src.core.config_migration import migrate_config_file_keys, migrate_config_values
from src.core.global_config_store import get_global_config
from src.data.lang import get_lang_accessor
from src.interaction.KeyConfig import KeyConfigManager
from src.interaction.ScreenPosition import ScreenPosition

_ok_screenshot.get_current_time_formatted = lambda: datetime.now().strftime("%Y%m%d_%H%M%S")


def _round_ratio(value):
    try:
        return round(float(value), 3)
    except Exception:
        return value


class BaseGameTask(BaseTask):
    """游戏自动化任务基类，提供通用的交互和识别功能。

    新项目从本类派生一次性任务；触发式任务继承
    ``BaseGameTask, TriggerTask``。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = ""  # 记录当前用户
        self.support_multi_account = False  # 是否支持多账号执行逻辑
        self.default_config_group = {}  # 配置项分组信息，格式为 { "分组名称": ["配置项1", "配置项2"] }
        self.box = ScreenPosition(self)  # 屏幕位置辅助对象，提供top/bottom/left/right等边界
        self.key_manager = KeyConfigManager(get_global_config("Game Hotkey Config"))
        self.once_sleep_time = get_global_config("Ensure Main Once Action Sleep").get(
            "SingleActionWithDelay", 1.5
        )  # 获取全局配置的单次动作睡眠时间

        # 语言访问器（按模块化 JSON 加载）
        try:
            self.lang = get_lang_accessor(self)
        except Exception:
            self.lang = get_lang_accessor(None)

        self._task_pause_started_at = None
        self._active_time_paused_total = 0.0
        self._seen_executor_pause_start = getattr(self.executor, "pause_start", None)

    # ── 暂停感知的活动计时 ─────────────────────────────
    def active_time(self) -> float:
        """Return monotonic task time with framework pauses excluded."""
        now = time.monotonic()
        executor = self.executor
        executor_pause_start = getattr(executor, "pause_start", None)
        current_executor_pause = 0.0

        if executor_pause_start != self._seen_executor_pause_start:
            pause_duration = max(0.0, time.time() - executor_pause_start)
            if executor.paused:
                current_executor_pause = pause_duration
            else:
                self._active_time_paused_total += pause_duration
                self._seen_executor_pause_start = executor_pause_start

        current_task_pause = 0.0
        if self._task_pause_started_at is not None:
            current_task_pause = max(0.0, now - self._task_pause_started_at)

        return now - self._active_time_paused_total - current_executor_pause - current_task_pause

    def sleep(self, timeout):
        """Sleep for active task time, keeping the deadline across pauses."""
        if timeout <= 0:
            return True

        deadline = self.active_time() + timeout
        while True:
            remaining = deadline - self.active_time()
            if remaining <= 0:
                return True
            super().sleep(min(remaining, 0.1))

    def pause(self):
        if not isinstance(self, TriggerTask) and self._task_pause_started_at is None:
            self._task_pause_started_at = time.monotonic()
        return super().pause()

    def unpause(self):
        if self._task_pause_started_at is not None:
            self._active_time_paused_total += max(0.0, time.monotonic() - self._task_pause_started_at)
            self._task_pause_started_at = None
        return super().unpause()

    def wait_until(self, condition, time_out=0, pre_action=None, post_action=None, settle_time=-1,
                   raise_if_not_found=False):
        """Framework wait_until variant whose timeout freezes while paused."""
        self.executor.reset_scene()
        start = self.active_time()
        if time_out == 0:
            time_out = self.executor.wait_scene_timeout
        settled = None

        while not self.executor.exit_event.is_set():
            if pre_action is not None:
                pre_action()
            self.next_frame()
            result = condition()
            if result:
                if settle_time == -1:
                    settle_time = self.executor.wait_until_settle_time
                if settle_time <= 0:
                    return result
                now = self.active_time()
                if settled is None:
                    settled = now
                elif now - settled > settle_time:
                    return result
                continue

            settled = None
            if post_action is not None:
                post_action()
            if self.active_time() - start > time_out:
                break

        if raise_if_not_found:
            raise WaitFailedException()
        return None

    # ── 坐标 / 点击辅助（把比例坐标四舍五入到 3 位小数） ──
    def box_of_screen(self, x=0, y=0, to_x=1.0, to_y=1.0, width=0.0, height=0.0,
                      name=None, hcenter=False, vcenter=False, confidence=1.0):
        return super().box_of_screen(
            _round_ratio(x), _round_ratio(y), _round_ratio(to_x), _round_ratio(to_y),
            width=width, height=height, name=name, hcenter=hcenter, vcenter=vcenter,
            confidence=confidence,
        )

    def box_of_screen_scaled(
        self,
        original_screen_width,
        original_screen_height,
        x_original,
        y_original,
        to_x=0,
        to_y=0,
        width_original=0,
        height_original=0,
        name=None,
        hcenter=False,
        vcenter=False,
        confidence=1.0,
    ):
        """Create a screen box scaled from original resolution coordinates with rounded ratios."""
        return super().box_of_screen_scaled(
            original_screen_width,
            original_screen_height,
            _round_ratio(x_original),
            _round_ratio(y_original),
            _round_ratio(to_x),
            _round_ratio(to_y),
            width_original=width_original,
            height_original=height_original,
            name=name,
            hcenter=hcenter,
            vcenter=vcenter,
            confidence=confidence,
        )

    def click_relative(self, x, y, *args, **kwargs):
        return super().click_relative(_round_ratio(x), _round_ratio(y), *args, **kwargs)

    def middle_click_relative(self, x, y, *args, **kwargs):
        """Middle-click at relative screen coordinates with rounded ratios."""
        return super().middle_click_relative(_round_ratio(x), _round_ratio(y), *args, **kwargs)

    @property
    def runtime_locale(self) -> str | None:
        """统一获取运行时 UI 语言。"""
        executor = getattr(self, "executor", None)
        locale_obj = getattr(executor, "locale", None)
        if locale_obj is None:
            return None
        if hasattr(locale_obj, "name"):
            try:
                name_attr = getattr(locale_obj, "name")
                value = name_attr() if callable(name_attr) else name_attr
                if value:
                    return str(value)
            except Exception:
                pass
        return str(locale_obj)

    # ── 配置键迁移 ──────────────────────────────────────
    def load_config(self):
        """走 MRO 收集各 mixin/任务的迁移表，执行键名复制与值转换迁移，再加载配置。

        先做纯键名复制（config_key_migrations），再做值转换（config_value_migrations），
        确保旧格式值（如布尔开关）在复制后仍能被正确转换为新格式（如列表）。
        """
        key_migrations = {}
        value_migrations = {}
        for klass in type(self).__mro__:
            table = getattr(klass, 'config_key_migrations', None)
            if table:
                key_migrations.update(table)
            vtable = getattr(klass, 'config_value_migrations', None)
            if vtable:
                value_migrations.update(vtable)
        migrate_config_file_keys(self.__class__.__name__, key_migrations)
        migrate_config_values(self.__class__.__name__, value_migrations)
        super().load_config()

    def handle_task_exception(self, e: Exception, prefix: str):
        """统一处理任务 run() 中的异常逻辑。

        - 截图（前缀基于日期 + prefix）
        - 根据配置 `发生异常时终止游戏` 决定是继续（记录日志）还是终止（记录并不抛出）
        - 对于 `TaskDisabledException` 总是重新抛出以便上层处理
        """
        try:
            self.screenshot(prefix)
        except Exception:
            pass

        if not self.config.get("发生异常时终止游戏", False):
            self.log_info("发生异常，继续游戏", notify=True)
            raise e
        else:
            if isinstance(e, TaskDisabledException):
                self.log_info("发生异常，继续游戏", notify=True)
                raise e
            else:
                self.log_info("发生异常，终止游戏", notify=True)

    def mark_task_failure(self, message: str, task_name: str | None = None):
        """统一标记任务失败消息，并截图（包含时间和任务名称）。"""
        name = task_name or getattr(self, "current_task", None) or "UnknownTask"
        try:
            self.screenshot(f"fail_{name}")
        except Exception:
            pass
        self.log_info(str(message))

    def ensure_main(self, recheck_time: float = 2, time_out: float = 90, **kwargs):
        """确保角色在主界面。暂未实现，调用时抛出 NotImplementedError。"""
        raise NotImplementedError(
            f"ensure_main(recheck_time={recheck_time}, time_out={time_out}) 尚未实现"
        )

    def register_config_groups(self, groups: dict, dropdown_name: str = "配置选择"):
        """注册配置分组，支持下拉切换 + 子配置折叠显示"""
        if not hasattr(self, "default_config") or self.default_config is None:
            self.default_config = {}

        if not hasattr(self, "config_type") or self.config_type is None:
            self.config_type = {}

        # 1. 创建下拉选择框
        dropdown_key = dropdown_name
        group_names = list(groups.keys())

        if not group_names:
            print("警告: groups 为空")
            return

        # 注册下拉框配置类型
        self.config_type[dropdown_key] = {
            "type": "drop_down",
            "options": group_names,
            "sub_configs": groups,  # 关键：用于框架实现折叠逻辑
        }

        # 2. 设置默认选中第一个分组
        self.default_config[dropdown_key] = group_names[0]

        # 3. 为所有配置项补充默认值（安全处理）
        for group_items in groups.values():
            for item in group_items:
                if isinstance(item, str):
                    key = item
                else:
                    key = str(item)

                if key not in self.default_config:
                    if hasattr(self, "config") and self.config is not None and key in self.config:
                        self.default_config[key] = self.config[key]
                    else:
                        self.default_config[key] = None

        self.config_description.update({
            dropdown_key: "配置默认隐藏，选择后展开对应配置项。"
        })