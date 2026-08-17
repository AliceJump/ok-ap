from ok import TriggerTask, Logger

from src.core.BaseGameTask import BaseGameTask
from src.icons import Icons

logger = Logger.get_logger(__name__)


class ExampleTriggerTask(BaseGameTask, TriggerTask):
    """触发式任务示例：每 5 秒检测一次全屏 OCR 并记录。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "示例触发任务"
        self.icon = Icons.Trigger
        self.description = "模板示例触发任务：周期性进行 OCR 检测并记录结果"
        self.trigger_interval = 5  # 避免过频繁轮询

        self.default_config = {
            '_enabled': False,
            '检测文本': '设置',
        }

    def run(self):
        target = self.config.get('检测文本', '设置')
        now = self.next_frame()
        boxes = self.ocr(match=target, frame=now)
        if boxes:
            self.log_info(f"识别到文本「{target}」，共 {len(boxes)} 处")
            return True
        return False