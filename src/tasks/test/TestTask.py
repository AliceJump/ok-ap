from src.core.BaseGameTask import BaseGameTask
from src.icons import Icons


class TestTask(BaseGameTask):
    """通用测试任务：验证任务框架可正常初始化与运行。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "框架自检"
        self.icon = Icons.Test
        self.description = "验证任务初始化、配置读取与日志输出是否正常"

    def run(self):
        self.log_info("框架自检通过：任务已初始化并可运行", notify=True)
        self.log_info(f"当前 UI 语言：{self.runtime_locale}")