# -*- coding: utf-8 -*-
# ruff: noqa: RUF002
"""由 tools/gen_lang_stubs.py 自动生成，请勿手改。

为 self.lang.<模块>.<key> 提供静态类型提示：
  - 自动补全：输入 self.lang.<模块>. 时列出全部 key
  - 悬浮提示：hover 显示该 key 在基准语言下的对应值

string 节点 -> str（运行时按当前 UI 语言取值，docstring 显示基准值）；
pattern 节点 -> re.Pattern[str]（docstring 显示文本）。
"""
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import LangModule as _LangModuleBase
    _LangModuleBaseT = _LangModuleBase
else:
    _LangModuleBaseT = object


class _LangAccessorTyped:
    """self.lang 的类型化声明（仅类型提示，运行时由 __getattr__ 动态加载）"""