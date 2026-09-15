import re

from src.core.BaseGameTask import BaseGameTask
from src.data.FeatureList import FeatureList
from src.icons import Icons
from src.image.hsv_config import HSVRange


class ExampleTask(BaseGameTask):
    """一次性任务示例：展示配置项、OCR 等待与模板匹配的基本用法。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "示例任务"
        self.icon = Icons.Task
        self.description = "模板示例任务：等待识别指定文本后点击并记录日志"

    
