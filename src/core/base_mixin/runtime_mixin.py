"""纯工具方法 Mixin：不覆写框架方法，只提供独立能力。"""

from __future__ import annotations

import gc
import threading
import time
from enum import Enum

import cv2
import numpy as np
from ok import Box

from src.config import config as app_config
from src.core.global_config_store import KEY_CONFIG_NAME, get_global_config
from src.data.FeatureList import FeatureList as fL
from src.image.frame_processes import isolate_by_hsv_ranges
from src.interaction.Key import move_keys as send_move_keys
from src.interaction.KeyConfig import KeyConfigManager
from src.interaction.Mouse import (
    active_and_send_mouse_delta as send_mouse_delta,
)
from src.interaction.Mouse import (
    move_to_target_once as move_to_target_once_impl,
)
from src.interaction.Mouse import (
    smooth_drag,
)
from src.yolo.loader import YoloModelLoader

feature_values = [f.value for f in fL]

import ctypes

import win32gui

_user32 = ctypes.windll.user32


def _find_window_by_class(class_name: str) -> int | None:
    """按类名查找窗口，返回 HWND 或 None。"""
    hwnd = _user32.FindWindowW(class_name, None)
    return hwnd if hwnd else None


class RuntimeMixin:
    """视觉识别、按键输入、鼠标控制与模型加载能力（纯工具方法）。"""

    BASE_WIDTH = 1920
    BASE_HEIGHT = 1080
    RESOLUTION_STABLE_SECONDS = 2.0
    RESOLUTION_STABLE_TIMEOUT = 6.0
    RESOLUTION_STABLE_INTERVAL = 0.1

    @property
    def GAME_CAPTURE_CONFIG(self) -> dict:
        """游戏窗口捕获配置（AzurPromilia.exe + UnityWndClass）。"""
        return {
            "windows": {
                "exe": app_config.get("windows", {}).get("exe", []),
                "hwnd_class": app_config.get("windows", {}).get("hwnd_class", "UnityWndClass"),
                "interaction": app_config.get("windows", {}).get("interaction", []),
                "capture_method": app_config.get("windows", {}).get("capture_method", ["WGC"]),
            },
        }

    @property
    def TOOL_WINDOW_CAPTURE_CONFIG(self) -> dict:
        """工具窗口捕获配置（同 exe + Qt5152QWindowToolSaveBits）。"""
        return {
            "windows": {
                "exe": app_config.get("windows", {}).get("exe", []),
                "hwnd_class": "Qt5152QWindowToolSaveBits",
            },
        }

    def find_tool_window_hwnd(self, tool_class: str = "Qt5152QWindowToolSaveBits") -> int:
        """在游戏主窗口的子窗口中查找工具覆盖窗口。"""
        game_hwnd = self.get_game_hwnd()
        if not game_hwnd:
            return 0
        result = [0]
        def enum_child(hwnd, _):
            if win32gui.GetClassName(hwnd) == tool_class:
                result[0] = hwnd
                return False
            return True
        try:
            win32gui.EnumChildWindows(game_hwnd, enum_child, None)
        except Exception:
            pass
        return result[0]

    # ── 坐标 / 窗口 ────────────────────────────────────

    def normalize_pos(self, pos):
        """
        将归一化坐标转换为当前窗口坐标。

        Args:
            pos: (x, y)，范围 [0, 1]

        Returns:
            tuple[int, int]
        """
        x, y = pos

        width = getattr(self, "width", self.BASE_WIDTH) or self.BASE_WIDTH
        height = getattr(self, "height", self.BASE_HEIGHT) or self.BASE_HEIGHT

        return (
            round(x * width),
            round(y * height),
        )

    def smooth_drag(self, start, end, duration=0.12):
        smooth_drag(
            self.get_game_hwnd(),
            self.normalize_pos(start),
            self.normalize_pos(end),
            duration,
        )

    def find_window_by_class(self, class_name: str) -> int | None:
        """按类名查找窗口，返回 HWND 或 None。"""
        return _find_window_by_class(class_name)

    def switch_to_window(self, class_name: str) -> int | None:
        """切换到指定类名的窗口，返回原游戏窗口 HWND（用于后续切回）。"""
        game_hwnd = self.get_game_hwnd()
        target_hwnd = _find_window_by_class(class_name)
        if target_hwnd:
            _user32.SetForegroundWindow(target_hwnd)
        return game_hwnd

    def switch_to_tool_window(self, class_name: str = "Qt5152QWindowToolSaveBits") -> int | None:
        """切换到工具窗口（如账号选择弹窗），返回原游戏窗口 HWND。"""
        return self.switch_to_window(class_name)

    def restore_game_window(self, game_hwnd: int | None = None):
        """恢复游戏窗口到前台。"""
        if game_hwnd:
            _user32.SetForegroundWindow(game_hwnd)
        else:
            self.ensure_in_front()

    # ── 捕获切换 ───────────────────────────────────────

    def ensure_capture(self, config: dict | None = None):
        """切换捕获目标窗口。

        Args:
            config: 捕获配置字典，格式参考 ok-nte 的 DynamicConfig。
                    包含 'windows' 键，值为 {'exe': ..., 'hwnd_class': ..., 'interaction': ...}。
                    不传则使用 self.capture_config。
        """
        if config is None:
            config = getattr(self, "capture_config", None)
        if config:
            return self.executor.device_manager.ensure_capture(config)

    def ensure_tool_window_capture(self):
        """切换捕获到游戏覆盖工具窗口（子窗口）。"""
        tool_hwnd = self.find_tool_window_hwnd()
        if not tool_hwnd:
            self.log_warning("工具覆盖窗口未找到")
            return
        config = {
            "windows": {
                "exe": app_config.get("windows", {}).get("exe", []),
                "selected_hwnd": tool_hwnd,
            },
        }
        return self.executor.device_manager.ensure_capture(config)

    # ── 分辨率 ─────────────────────────────────────────

    _resolution_warned = False

    def feature_stable(self, feature, box, duration):
        if duration <= 0:
            return True

        end_time = time.time() + duration
        while time.time() < end_time:
            if not self.find_feature(feature_name=feature, box=box, frame=self.next_frame()):
                return False
            self.sleep(0.05)

        return True

    def click_feature(
        self,
        feature,
        boxes=None,
        time_out=5,
        after_sleep=0,
        click_after_delay=0,
        settle_time=0,
        blind_point=None,
        blind_delay=1,
        verify_disappear=True,
        verify_timeout=0.5,
        max_click_retry=3,
    ):
        boxes = [None] + (boxes or [])

        start_time = time.time()
        last_blind_time = 0

        while time.time() - start_time < time_out:
            frame = self.next_frame()

            for box in boxes:
                result = self.find_feature(
                    feature_name=feature,
                    box=box,
                    frame=frame,
                )

                if result and self.feature_stable(feature, box, settle_time):
                    retry_count = 0

                    while retry_count < max_click_retry:
                        self.sleep(click_after_delay)

                        self.click(result, after_sleep=after_sleep)

                        if not verify_disappear:
                            return True

                        if self.wait_feature_disappear(
                            feature,
                            box,
                            verify_timeout,
                        ):
                            return True

                        self.log_warning(f"{feature} 点击后未消失，重试 {retry_count + 1}/{max_click_retry}")

                        retry_count += 1

            if blind_point and (time.time() - last_blind_time >= blind_delay):
                self.click(
                    blind_point[0],
                    blind_point[1],
                    after_sleep=after_sleep,
                )
                last_blind_time = time.time()

        return False

    def wait_feature_disappear(
        self,
        feature,
        box=None,
        timeout=1,
    ):
        start = time.time()

        while time.time() - start < timeout:
            frame = self.next_frame()

            if not self.find_feature(
                feature_name=feature,
                box=box,
                frame=frame,
            ):
                return True

        return False

    def _wait_for_stable_resolution(self):
        """等待捕获帧尺寸稳定，避免启动阶段的中间帧触发误报。"""
        next_frame = getattr(self, "next_frame", None)
        if not callable(next_frame):
            width = getattr(self, "width", self.BASE_WIDTH) or self.BASE_WIDTH
            height = getattr(self, "height", self.BASE_HEIGHT) or self.BASE_HEIGHT
            return int(width), int(height)

        deadline = time.monotonic() + self.RESOLUTION_STABLE_TIMEOUT
        last_resolution = None
        stable_since = None
        resolution = None

        while time.monotonic() < deadline:
            try:
                frame = next_frame()
                if frame is not None and getattr(frame, "ndim", 0) >= 2:
                    resolution = (int(frame.shape[1]), int(frame.shape[0]))
            except Exception:
                pass

            if resolution is None:
                width = getattr(self, "width", self.BASE_WIDTH) or self.BASE_WIDTH
                height = getattr(self, "height", self.BASE_HEIGHT) or self.BASE_HEIGHT
                resolution = (int(width), int(height))

            now = time.monotonic()
            if resolution != last_resolution:
                last_resolution = resolution
                stable_since = now
            elif stable_since is not None and now - stable_since >= self.RESOLUTION_STABLE_SECONDS:
                return resolution

            time.sleep(self.RESOLUTION_STABLE_INTERVAL)

        return resolution or (self.BASE_WIDTH, self.BASE_HEIGHT)

    def check_resolution(self):
        if RuntimeMixin._resolution_warned:
            return
        width, height = self._wait_for_stable_resolution()
        min_size = app_config.get("supported_resolution", {}).get("min_size", (1920, 1080))
        min_w, min_h = min_size
        if width < min_w or height < min_h:
            self.log_info(
                f"当前分辨率 {width}x{height} 低于要求最小值 {min_w}x{min_h}（1080P），不保证正常运行", notify=True
            )
        RuntimeMixin._resolution_warned = True

    def resolution_scale(self) -> float:
        """
        返回当前分辨率相对于基准分辨率的缩放系数。

        Returns:
            float: 当前窗口分辨率相对于基准分辨率的缩放比例。
        """
        width = getattr(self, "width", self.BASE_WIDTH) or self.BASE_WIDTH
        height = getattr(self, "height", self.BASE_HEIGHT) or self.BASE_HEIGHT
        return min(width / self.BASE_WIDTH, height / self.BASE_HEIGHT)

    def scale_distance(self, value: int | float, minimum: int = 1) -> int:
        """
        按当前分辨率缩放距离并保证不小于最小值。

        Args:
            value: 原始距离值。
            minimum: 缩放后的最小返回值。

        Returns:
            int: 缩放后的距离。
        """
        return max(minimum, int(round(value * self.resolution_scale())))

    def get_feature_by_resolution(self, base_name: str):
        """
        根据当前分辨率选择最合适的资源后缀。

        Args:
            base_name: 资源基础名称。

        Returns:
            str: 匹配到的资源名称。

        Raises:
            AttributeError: 当没有任何可用资源时抛出。
        """
        cache_key = (base_name, self.width)

        if not hasattr(self, "_feature_cache"):
            self._feature_cache = {}

        if cache_key in self._feature_cache:
            return self._feature_cache[cache_key]

        if self.width >= 3800:
            suffixes = ("_4k", "_2k", "")
        elif self.width >= 2500:
            suffixes = ("_2k", "_4k", "")
        else:
            suffixes = ("", "_2k", "_4k")

        for suffix in suffixes:
            feature_name = base_name + suffix
            if feature_name in feature_values:
                self._feature_cache[cache_key] = feature_name
                return feature_name

        raise AttributeError(f"未找到任何可用资源: {base_name}")

    # ── 特征等待 / 点击 ────────────────────────────────

    def safe_back(self, match=None, feature=None, box=None, time_out: float = 30, once_time_out: float = 2):
        """
        安全返回：持续点击返回直到找到指定目标（OCR文本或特征）。

        Args:
            match: 需要等待出现的 OCR 文本。
            feature: 需要等待出现的特征名。
            box: 识别范围。
            time_out: 总超时时间。
            once_time_out: 单次等待超时。

        Returns:
            bool: 是否成功找到目标。
        """
        if match is None and feature is None:
            self.log_warning("safe_back 被调用时 match 和 feature 都为空")
            return False

        start_time = self.active_time()

        while True:
            if self.active_time() - start_time > time_out:
                self.log_info(self.tr("safe_back 超时（{time_out}s），目标未出现").format(time_out=time_out))
                return False

            remaining = time_out - (self.active_time() - start_time)

            def target_visible():
                if match is not None and self.ocr(match=match, box=box):
                    return True
                if feature is not None and self.find_one(
                    feature,
                    vertical_variance=0.05,
                    horizontal_variance=0.05,
                    box=box,
                ):
                    return True
                return False

            if self.wait_until(
                target_visible,
                time_out=max(0.01, min(once_time_out, remaining)),
                raise_if_not_found=False,
            ):
                return True

            self.log_info("safe_back 观察超时，发送返回键")
            self.back()

    # ── 全局点击 ───────────────────────────────────────

    def click_at(
        self,
        x: int = -1,
        y: int = -1,
        alt: bool = False,
        activate: bool = False,
        after_sleep: float = 0,
    ):
        """统一点击入口，通过 pyautogui 在窗口指定位置点击。

        Args:
            x, y: 窗口客户区坐标（-1 表示窗口中心）。
            alt: True 时按住 Alt 再点击。
            activate: True 时先激活窗口到前台。
            after_sleep: 点击后等待时间。
        """
        import pyautogui

        from src.interaction.Mouse import run_at_window_pos

        if activate:
            self.active_and_send_mouse_delta(0, 0, activate=True, only_activate=True)
            self.sleep(0.1)

        hwnd = self.get_game_hwnd()
        if x < 0 or y < 0:
            x = round(self.width * 0.5)
            y = round(self.height * 0.5)

        if alt:
            self.send_key_down("alt")
            self.sleep(0.5)
            run_at_window_pos(hwnd, pyautogui.click, x, y)
            self.send_key_up("alt")
        else:
            run_at_window_pos(hwnd, pyautogui.click, x, y)

        if after_sleep > 0:
            self.sleep(after_sleep)

    def click_at_box(self, box, relative_x=0.5, relative_y=0.5, alt=False, activate=True, after_sleep=0):
        """点击 Box 对象的指定相对位置。"""
        if isinstance(box, list):
            box = box[0]
        x, y = box.relative_with_variance(relative_x, relative_y)
        self.click_at(x, y, alt=alt, activate=activate, after_sleep=after_sleep)

    # ── YOLO ───────────────────────────────────────────

    def yolo_loader(self) -> YoloModelLoader:
        """
        返回当前任务使用的 YOLO 加载器实例。

        Returns:
            YoloModelLoader: 当前任务的 YOLO 加载器。
        """
        loader = getattr(self, "_yolo_loader", None)
        if loader is not None:
            return loader

        lock = getattr(self, "_detector_lock", None)
        if lock is None:
            return self._create_yolo_loader()

        with lock:
            loader = getattr(self, "_yolo_loader", None)
            if loader is None:
                loader = self._create_yolo_loader()
            return loader

    def _create_yolo_loader(self) -> YoloModelLoader:
        yolo_config = app_config.get("yolo", {})
        self._yolo_loader = YoloModelLoader(yolo_config)
        if not getattr(self, "_yolo_model_key", None):
            self._yolo_model_key = self._yolo_loader.default_model_key
        return self._yolo_loader

    @property
    def detector(self):
        return self.set_yolo_model(getattr(self, "_yolo_model_key", None) or self.yolo_loader().default_model_key)

    def release_yolo_detector(self):
        lock = getattr(self, "_detector_lock", None)
        if lock is None:
            self._release_yolo_detector_unlocked()
            return

        with lock:
            self._release_yolo_detector_unlocked()

    def _release_yolo_detector_unlocked(self):
        loader = getattr(self, "_yolo_loader", None)
        detector = getattr(self, "_detector", None)

        if loader is not None and hasattr(loader, "release"):
            loader.release()
        elif detector is not None and hasattr(detector, "release"):
            detector.release()

        self._detector = None
        self._yolo_loader = None
        self._yolo_model_key = None
        gc.collect()

    def list_yolo_targets(self, model_key: str | None = None) -> list[str]:
        return self.yolo_loader().target_names(model_key or self._yolo_model_key)

    def set_yolo_model(self, model_key: str):
        loader = self.yolo_loader()
        key = model_key or loader.default_model_key
        self._detector = loader.get_detector(key)
        self._yolo_model_key = key
        return self._detector

    # ── HSV / 稳定性 ───────────────────────────────────

    def make_hsv_isolator(self, ranges, invert=True, kernel_size=2):
        """返回一个可直接调用的 HSV 过滤函数"""
        return lambda frame: isolate_by_hsv_ranges(
            frame,
            ranges,
            invert=invert,
            kernel_size=kernel_size,
        )

    def _is_debug_overlay_enabled(self) -> bool:
        config_holders = (
            getattr(self, "executor", None),
            self,
        )
        for holder in config_holders:
            ok_config = getattr(holder, "ok_config", None)
            if ok_config is None:
                continue
            getter = getattr(ok_config, "get", None)
            if callable(getter):
                return bool(getter("use_overlay", False))

        try:
            from ok import og

            app = getattr(og, "app", None)
            ok_config = getattr(app, "ok_config", None)
            getter = getattr(ok_config, "get", None)
            if callable(getter):
                return bool(getter("use_overlay", False))
        except Exception:
            pass

        return False

    def yolo_detect(
        self,
        name: str | list[str],
        frame: np.ndarray | None = None,
        box: Box | None = None,
        conf: float = 0.7,
        detections: list[Box] | None = None,
        model_key: str | None = None,
    ) -> list[Box]:
        """
        对当前帧执行 YOLO 检测并返回命中的框。

        Args:
            name: 目标名称或名称列表。
            frame: 输入图像帧。
            box: 裁剪检测区域。
            conf: 置信度阈值。
            detections: 外部提供的检测结果。
            model_key: 指定的模型键。

        Returns:
            list[Box]: 命中的检测框，按置信度降序排列。

        Raises:
            ValueError: 当 name 为空或无效时抛出。
        """
        if not name:
            raise ValueError("yolo_detect 至少需要传入一个 name")
        raw_names = [name] if isinstance(name, str) else name
        ordered_target_names = [str(n.value) if isinstance(n, Enum) else str(n) for n in raw_names if n is not None]
        target_names = {n for n in ordered_target_names}
        if not ordered_target_names:
            raise ValueError("yolo_detect 至少需要一个有效 name")

        frame = frame if frame is not None else self.next_frame()
        if frame is None:
            return []

        offset_x = 0
        offset_y = 0
        detect_frame = frame

        if box is not None:
            detect_frame = box.crop_frame(frame)
            offset_x = int(box.x)
            offset_y = int(box.y)

        if detections is None:
            if model_key is None:
                loader = self.yolo_loader()
                first_name = ordered_target_names[0]
                resolved_model_key, detector = loader.get_detector_for_name(first_name)
                self._yolo_model_key = resolved_model_key
                self._detector = detector
            else:
                detector = self.set_yolo_model(model_key)
            if detector is None:
                self.log_error("yolo_detect: detector is not available")
                return []
            detections = detector.detect(detect_frame, threshold=conf)
        detections = detections or []

        self.log_info(self.tr("yolo_detect: raw detections count = {count}").format(count=len(detections)))
        raw_results: list[Box] = []
        filtered_results: list[Box] = []

        for det in detections:
            if not all(hasattr(det, attr) for attr in ("x", "y", "width", "height")):
                continue
            det_name = getattr(det, "name", None)
            det_conf = float(getattr(det, "confidence", 0.0) or 0.0)
            self.log_info(self.tr("Raw detection: name={name}, conf={conf:.3f}").format(name=det_name, conf=det_conf))

            new_box = Box(
                int(det.x + offset_x),
                int(det.y + offset_y),
                int(det.width),
                int(det.height),
            )

            new_box.name = det_name
            new_box.confidence = det_conf
            raw_results.append(new_box)

            if det_name in target_names:
                filtered_results.append(new_box)

        debug_overlay_enabled = self._is_debug_overlay_enabled()
        if debug_overlay_enabled:
            debug_tag = "_".join(sorted(target_names)) or "no_target"
            self.draw_boxes(f"yolo_raw_{debug_tag}", raw_results, color="yellow", debug=debug_overlay_enabled)
            self.draw_boxes(f"yolo_filtered_{debug_tag}", filtered_results, color="red", debug=debug_overlay_enabled)

        self.log_info(self.tr("yolo_detect: filtered detections count = {count}").format(count=len(filtered_results)))

        return sorted(filtered_results, key=lambda item: item.confidence, reverse=True)

    def wait_ui_stable(
        self,
        method="phash",
        threshold: int | float = 5,
        stable_time: float = 0.5,
        max_wait: float = 5,
        refresh_interval: float = 1,
        box: Box | tuple | list | None = None,
        ssim_threshold: float = 0.95,
    ):
        """
        等待指定区域在视觉上稳定下来。

        Args:
            method: 稳定性判断方法（phash/dhash/pixel/ssim）。
            threshold: 稳定阈值（phash/dhash 为汉明距离，pixel 为像素差异均值）。
            stable_time: 持续稳定时长。
            max_wait: 最长等待时间。
            refresh_interval: 帧刷新间隔。
            box: 需要监测的区域。
            ssim_threshold: SSIM 方法专用阈值（0-1 范围，默认 0.95）。

        Returns:
            bool: 稳定后返回 True，超时返回 False。

        Raises:
            ValueError: 当 method 不支持或 box 非法时抛出。
        """

        def parse_box(frame, box: Box | tuple | list | None):
            if box is None:
                return frame

            if hasattr(box, "x"):
                x = int(box.x)
                y = int(box.y)
                w = int(box.width)
                h = int(box.height)
                return frame[y : y + h, x : x + w]

            if isinstance(box, (tuple, list)) and len(box) == 4:
                x, y, w, h = map(int, box)
                return frame[y : y + h, x : x + w]

            raise ValueError("box must be None / (x,y,w,h) / object(x,y,width,height)")

        start_time = self.active_time()
        last_frame = parse_box(self.next_frame(), box)
        stable_start = None
        last_hash = None
        if method in ("phash", "dhash"):
            from src.image.stability import hamming_distance, perceptual_hash

            last_hash = perceptual_hash(last_frame, method=method)

        while True:
            current_frame = parse_box(self.next_frame(), box)

            if method in ("phash", "dhash"):
                h2 = perceptual_hash(current_frame, method=method)
                is_stable = hamming_distance(last_hash, h2) <= threshold
                last_hash = h2

            elif method == "pixel":
                if last_frame.shape != current_frame.shape:
                    is_stable = False
                else:
                    diff = cv2.absdiff(last_frame, current_frame)
                    is_stable = np.mean(diff) <= threshold

            elif method == "ssim":
                from src.image.stability import ssim_score

                if last_frame.shape != current_frame.shape:
                    is_stable = False
                else:
                    is_stable = ssim_score(last_frame, current_frame) >= ssim_threshold

            else:
                raise ValueError(f"Unknown method {method}")

            if is_stable:
                if stable_start is None:
                    stable_start = self.active_time()
                elif self.active_time() - stable_start >= stable_time:
                    return True
            else:
                stable_start = None

            if self.active_time() - start_time > max_wait:
                return False

            last_frame = current_frame
            self.sleep(refresh_interval)

    # ── 按键 / 移动 ────────────────────────────────────

    def _account_key_config(self) -> dict:
        """全局键位配置叠加当前账号覆盖后的有效键位表（无账号上下文时为全局原值）。"""
        base_config = get_global_config(KEY_CONFIG_NAME)
        override = self._account_override_for(KEY_CONFIG_NAME)
        if not override:
            return base_config
        effective = dict(base_config)
        for key, value in override.items():
            if key in base_config:
                effective[key] = self._coerce_override_value(base_config[key], value)
        return effective

    def _resolve_config_key(self, key: str, key_type: str) -> str:
        """按当前账号上下文解析实际按键。"""
        return KeyConfigManager(self._account_key_config()).resolve_key(key, key_type)

    def press_key(self, key: str, down_time: float = 0.02, after_sleep: float = 0, interval: int = -1):
        """
        按配置映射后的通用按键。

        Args:
            key: 按键名称。
            down_time: 按下时长。
            after_sleep: 释放后等待时间。
            interval: 按键间隔。

        Returns:
            Any: send_key 的返回值。
        """
        actual_key = self._resolve_config_key(key, "common")
        return self.send_key(actual_key, interval=interval, down_time=down_time, after_sleep=after_sleep)

    def press_combat_key(self, key: str, down_time: float = 0.02, after_sleep: float = 0, interval: int = -1):
        """
        按配置映射后的战斗按键。

        Args:
            key: 按键名称。
            down_time: 按下时长。
            after_sleep: 释放后等待时间。
            interval: 按键间隔。

        Returns:
            Any: send_key 的返回值。
        """
        actual_key = self._resolve_config_key(key, "combat")
        return self.send_key(actual_key, interval=interval, down_time=down_time, after_sleep=after_sleep)

    def move_keys(self, keys, duration, need_back=False):
        """
        在窗口中持续按下移动键。

        Args:
            keys: 按键序列。
            duration: 持续时间。
            need_back: 结束后是否恢复窗口焦点。

        Returns:
            None
        """
        send_move_keys(self, keys, duration)

    def _dodge_with_direction(
        self, direction_key: str, pre_hold: float = 0.004, dodge_down_time: float = 0.003, after_sleep: float = 0.005
    ):
        """
        按指定方向执行闪避。

        Args:
            direction_key: 方向键。
            pre_hold: 闪避前预按时长。
            dodge_down_time: 闪避键按下时长。
            after_sleep: 闪避后等待时间。

        Returns:
            None
        """
        move_thread = threading.Thread(target=self.move_keys, args=(direction_key, pre_hold), daemon=True)
        move_thread.start()
        self.sleep(0.005)
        self.press_key("lshift", down_time=dodge_down_time)
        move_thread.join(timeout=max(pre_hold + 0.002, 0.05))
        if after_sleep > 0:
            self.sleep(after_sleep)

    def dodge_forward(self, pre_hold: float = 0.004, dodge_down_time: float = 0.003, after_sleep: float = 0.005):
        """
        向前闪避。

        Args:
            pre_hold: 闪避前预按时长。
            dodge_down_time: 闪避键按下时长。
            after_sleep: 闪避后等待时间。

        Returns:
            None
        """
        self._dodge_with_direction("w", pre_hold=pre_hold, dodge_down_time=dodge_down_time, after_sleep=after_sleep)

    def screen_center(self) -> tuple[int, int]:
        """
        返回当前屏幕中心点坐标。

        Returns:
            tuple[int, int]: 屏幕中心点坐标。
        """
        return int(self.width / 2), int(self.height / 2)

    def move_to_target_once(self, ocr_obj, max_step=100, min_step=20, slow_radius=200, deadzone=4):
        """
        移动一次以逼近 OCR 目标。

        Args:
            ocr_obj: OCR 目标对象。
            max_step: 最大步长。
            min_step: 最小步长。
            slow_radius: 减速半径。
            deadzone: 误差死区。

        Returns:
            Any: move_to_target_once_impl 的返回值。
        """
        scaled_max_step = self.scale_distance(max_step)
        scaled_min_step = min(scaled_max_step, self.scale_distance(min_step))
        scaled_slow_radius = self.scale_distance(slow_radius)
        scaled_deadzone = self.scale_distance(deadzone)
        return move_to_target_once_impl(
            self.get_game_hwnd(),
            ocr_obj,
            self.screen_center,
            max_step=scaled_max_step,
            min_step=scaled_min_step,
            slow_radius=scaled_slow_radius,
            deadzone=scaled_deadzone,
        )

    def active_and_send_mouse_delta(self, dx=1, dy=1, activate=True, only_activate=False, delay=0.02, steps=3) -> bool:
        """
        激活窗口后发送鼠标位移。

        Args:
            dx: 水平位移。
            dy: 垂直位移。
            activate: 是否激活窗口。
            only_activate: 是否只激活不移动。
            delay: 步进间隔延迟。
            steps: 步进次数。

        Returns:
            bool: 请求激活时窗口是否成功成为前台窗口；未请求激活时返回 True。
        """
        return send_mouse_delta(self.get_game_hwnd(), dx, dy, activate, only_activate, delay, steps)

    def click_with_alt(
        self,
        x: int | float | Box | list[Box] = -1,
        y: int | float = -1,
        move_back: bool = False,
        name: str | None = None,
        interval: int = -1,
        move: bool = True,
        down_time: float = 0.01,
        after_sleep: float = 0,
        key: str = "left",
    ):
        self.send_key_down("alt")
        self.sleep(0.5)
        self.click(
            x=x,
            y=y,
            move_back=move_back,
            name=name,
            interval=interval,
            move=move,
            down_time=down_time,
            after_sleep=after_sleep,
            key=key,
        )
        self.send_key_up("alt")

    # ── 组合等待点击 ───────────────────────────────────

    def wait_click_feature(
        self,
        feature,
        horizontal_variance=0,
        vertical_variance=0,
        threshold=0,
        relative_x=0.5,
        relative_y=0.5,
        time_out=0,
        pre_action=None,
        post_action=None,
        box=None,
        raise_if_not_found=True,
        use_gray_scale=False,
        canny_lower=0,
        canny_higher=0,
        click_after_delay=0,
        settle_time=-1,
        after_sleep=0,
        target_height=0,
        alt: bool = False,
    ):
        result = self.wait_until(
            lambda: self.find_one(
                feature,
                horizontal_variance,
                vertical_variance,
                threshold,
                box=box,
                use_gray_scale=use_gray_scale,
                canny_lower=canny_lower,
                canny_higher=canny_higher,
                target_height=target_height,
            ),
            time_out=time_out,
            pre_action=pre_action,
            post_action=post_action,
            raise_if_not_found=raise_if_not_found,
            settle_time=settle_time,
        )
        if result is not None:
            if click_after_delay > 0:
                self.sleep(click_after_delay)
            if alt:
                x, y = result.relative_with_variance(relative_x, relative_y)
                self.click_with_alt(x, y, name=result.name, after_sleep=after_sleep)
            else:
                self.click_box(result, relative_x, relative_y, after_sleep=after_sleep)
            return True
        return False

    def wait_click_ocr(
        self,
        x=0,
        y=0,
        to_x=1,
        to_y=1,
        width=0,
        height=0,
        box=None,
        name=None,
        match=None,
        threshold=0,
        frame=None,
        target_height=0,
        time_out=0,
        raise_if_not_found=False,
        recheck_time=0,
        after_sleep=0,
        post_action=None,
        log=False,
        screenshot=False,
        settle_time=-1,
        lib="default",
        alt: bool = False,
    ):
        """
        等待 OCR 命中后立即点击目标。

        Args:
            x: 区域左上角相对 X 坐标。
            y: 区域左上角相对 Y 坐标。
            to_x: 区域右下角相对 X 坐标。
            to_y: 区域右下角相对 Y 坐标。
            width: 识别区域宽度。
            height: 识别区域高度。
            box: 识别框。
            name: 识别区域名称。
            match: 需要匹配的文本或正则。
            threshold: OCR 置信度阈值。
            frame: 输入帧。
            target_height: 目标缩放高度。
            time_out: 等待超时时间。
            raise_if_not_found: 是否在未找到时抛异常。
            recheck_time: 复检等待时间。
            after_sleep: 点击后等待时间。
            post_action: 后置动作。
            log: 是否记录日志。
            screenshot: 是否截图。
            settle_time: 稳定等待时间。
            lib: OCR 引擎名称。
            alt: 是否使用 alt+click。

        Returns:
            Any: 命中时返回 OCR 结果，否则返回 None。
        """
        result = self.wait_ocr(
            x,
            y,
            width=width,
            height=height,
            to_x=to_x,
            to_y=to_y,
            box=box,
            name=name,
            match=match,
            threshold=threshold,
            frame=frame,
            target_height=target_height,
            time_out=time_out,
            raise_if_not_found=raise_if_not_found,
            post_action=post_action,
            log=log,
            screenshot=screenshot,
            settle_time=settle_time,
            lib=lib,
        )
        if recheck_time > 0:
            self.sleep(recheck_time)
            result = self.ocr(
                x,
                y,
                width=width,
                height=height,
                to_x=to_x,
                to_y=to_y,
                box=box,
                name=name,
                match=match,
                threshold=threshold,
                frame=frame,
                target_height=target_height,
                log=log,
                screenshot=screenshot,
                lib=lib,
            )

        if result is not None:
            if alt:
                self.click_with_alt(result, after_sleep=after_sleep)
            else:
                self.click(result, after_sleep=after_sleep)
            return result

        if isinstance(match, (list, tuple)):
            match_text = [getattr(m, "pattern", m) for m in match]
        else:
            match_text = getattr(match, "pattern", match)
        self.log_info(
            self.tr("wait ocr no box {x} {y} {width} {height} {to_x} {to_y} {match}").format(
                x=x, y=y, width=width, height=height, to_x=to_x, to_y=to_y, match=match_text
            )
        )
