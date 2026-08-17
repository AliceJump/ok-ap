"""自定义图标模块。

模板默认直接复用 qfluentwidgets 的 FluentIcon，无需任何图标资源文件。
如需自定义图标（浅色/深色双变体、GIF 动图），可参照原 ok-end-field 项目
的 src/icons.py：基于 FluentIconBase 实现 ThemeIcon / GifIcon。
"""
from qfluentwidgets import FluentIcon


class Icons:
    """统一图标入口：替换成项目自己的图标类后可全局生效。"""

    Default = FluentIcon.APPLICATION
    Task = FluentIcon.GAME
    Trigger = FluentIcon.SYNC
    Test = FluentIcon.ROBOT
    Config = FluentIcon.SETTING
    Account = FluentIcon.PEOPLE
    Keyboard = FluentIcon.SETTING
    Interaction = FluentIcon.PLAY