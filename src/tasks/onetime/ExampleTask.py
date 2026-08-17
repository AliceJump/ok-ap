from src.core.BaseGameTask import BaseGameTask
from src.icons import Icons


class ExampleTask(BaseGameTask):
    """一次性任务示例：展示配置项、OCR 等待与模板匹配的基本用法。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "示例任务"
        self.icon = Icons.Task
        self.description = "模板示例任务：等待识别指定文本后点击并记录日志"

        self.default_config = {
            "等待时间(秒)": 5,
            "目标文本": "开始",
        }
        self.config_description = {
            "等待时间(秒)": "等待目标文本出现的最长时间（秒）。",
            "目标文本": "要匹配的 OCR 文本。",
        }

    def run(self):
        timeout = self.config.get("等待时间(秒)", 5)
        target = self.config.get("目标文本", "开始")
        self.log_info(f"开始执行示例任务，等待文本「{target}」出现，超时 {timeout} 秒", notify=True)

        result = self.wait_ocr(match=target, time_out=timeout, raise_if_not_found=False)
        if result:
            self.click_box(result, after_sleep=0.5)
            self.log_info("已识别并点击目标文本", notify=True)
        else:
            self.log_warning(f"在 {timeout} 秒内未识别到文本「{target}」")