from enum import Enum


class HSVRange(tuple, Enum):
    # ((h_min, s_min, v_min), (h_max, s_max, v_max))
    # 白色文本，特殊典例:上滑索时，可移动但未锁定到的滑索距离数字文本
    WHITE = (((0, 0, 200), (180, 50, 255)),)
    # 黄色文本，特殊典例:上滑索时，可移动且已被锁定到的滑索距离数字文本
    GOLD_TEXT = (((15, 40, 180), (60, 180, 255)),)
    # 灰色文本，特殊典例:倒卖页面的价格文本和好友名称
    DARK_GRAY_TEXT = (((0, 0, 40), (180, 30, 90)),)
