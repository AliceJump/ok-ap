"""一键日常任务示例。

展示如何使用迁移的 DailyTaskRunner、daily_summary 和 AccountMixin
来构建一个支持多账户的日常任务。

职责：
1. 注册配置（包括多账户配置）
2. 声明任务清单（build_task_plan）
3. 驱动编排器（run）
4. 生成执行汇总报告
"""

import tempfile
from pathlib import Path

from src.core.BaseGameTask import BaseGameTask
from src.icons import Icons
from src.tasks.daily.account_mixin import AccountMixin
from src.tasks.daily.daily_summary import create_task_summary_report, open_local_path_with_default_app
from src.tasks.daily.daily_task_runner import DailyTaskRunner


class DailyTask(AccountMixin, BaseGameTask):
    """一键日常任务：展示多账户、任务编排与汇总报告的完整用法。

    继承顺序：AccountMixin 在前，确保多账户能力注入。
    """

    # 允许「多账户独立配置」按账号覆盖本任务的参数
    support_multi_account = True

    # 这些是全账号共用的开关，按账号覆盖没有意义
    account_config_blacklist = {
        "生成汇总文件",
        "自动打开汇总文件",
        "Exit After Task",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "一键日常"
        self.icon = Icons.Task
        self.description = "日常任务编排示例：多账户 + 任务清单 + 汇总报告"
        self.support_schedule_task = True
        self.daily_runner = None  # DailyTaskRunner 实例

        # 初始化多账户配置（必须在 super().__init__ 之后）
        self._init_account_config()
        # 初始化本任务的默认配置
        self._init_default_config()

    def _init_default_config(self):
        """注册日常任务的配置项。"""
        self.default_config.update({
            "收邮件": True,
            "领奖励": True,
            "刷副本": False,
            "生成汇总文件": True,
            "自动打开汇总文件": False,
        })
        self.config_description.update({
            "收邮件": "自动收取游戏内邮件奖励",
            "领奖励": "自动领取日常奖励",
            "刷副本": "自动刷取指定副本",
            "生成汇总文件": (
                "任务结束后把执行情况写成 txt 汇总\n"
                "目录：系统临时目录/ok-ap/一键日常/"
            ),
            "自动打开汇总文件": "生成汇总后自动用系统默认程序打开它",
        })

    # ── 任务清单 ──────────────────────────────────────────

    def build_task_plan(self):
        """声明日常任务执行清单。

        元素为 (任务名, 执行函数)，任务名同时是配置开关的键名。
        需要自定义开关判定时追加第三个元素「开关谓词」。

        顺序与开关语义与改造前的 run() 完全一致。
        """
        return [
            # 内置项，不做开关判定，恒执行
            ("收邮件", self.collect_mail),
        ]

    # ── 各任务项的具体实现（示例） ────────────────────────

    def collect_mail(self):
        """收邮件（示例实现）。"""
        self.log_info("开始收取邮件...", notify=True)
        # 实际实现中，这里会有 OCR/特征匹配/点击逻辑
        # 示例：等待并点击邮件入口
        # result = self.wait_ocr(match="邮件", time_out=10, raise_if_not_found=False)
        # if result:
        #     self.click_box(result)
        #     self.wait_click_ocr(match="一键领取", time_out=5)
        self.sleep(1)
        self.log_info("邮件收取完成", notify=True)
        return True

    # ── 主执行入口 ────────────────────────────────────────

    def run(self):
        """任务主入口：驱动 DailyTaskRunner 执行任务清单。"""
        try:
            self.daily_runner = DailyTaskRunner(self, self.build_task_plan())
            self.daily_runner.run()
        finally:
            # 无论正常结束还是异常中断，都尝试落地汇总
            self.run_daily_finally()

    def run_daily_finally(self):
        """生成执行情况汇总 txt。整个过程失败只记日志，不影响任务本身的结果。"""
        try:
            if not self.config.get("生成汇总文件", True):
                return True
            if not (self.daily_runner and self.daily_runner.has_summary_data()):
                self.log_info("无可用汇总信息，跳过生成汇总文件")
                return True

            summary_path = create_task_summary_report(
                self, Path(tempfile.gettempdir()), self.daily_runner.final_summary
            )
            if self.config.get("自动打开汇总文件", False):
                open_local_path_with_default_app(summary_path)
                self.log_info(f"日常执行情况汇总已创建并打开: {summary_path}")
            else:
                self.log_info(f"日常执行情况汇总已创建（未打开）: {summary_path}")
            return True
        except Exception as e:
            self.log_info(f"创建日常任务汇总文件失败: {e}", notify=True)
            return False

