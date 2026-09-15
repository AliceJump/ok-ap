from __future__ import annotations

_PATCH_INSTALLED = False


def install_qfluent_navigation_patch():
    """Fix qfluentwidgets NavigationPanel crash when expand() is called
    before window is visible (_findIndicatorItem returns None)."""
    global _PATCH_INSTALLED
    if _PATCH_INSTALLED:
        return
    try:
        from qfluentwidgets.components.navigation.navigation_panel import NavigationPanel
    except Exception:
        return
    logger = None
    originals = {
        "_onIndicatorAniFinished": NavigationPanel._onIndicatorAniFinished,
    }
    try:
        from ok import Logger
        logger = Logger.get_logger(__name__)
    except Exception:
        pass

    def _patched_on_indicator_ani_finished(self):
        item = self.currentItem()
        if not item:
            return
        item.setSelected(True)
        indicator_item = self._findIndicatorItem(item)
        if indicator_item is not None:
            indicator_item.setAboutSelected(False)
        self.indicator.hide()

    try:
        NavigationPanel._onIndicatorAniFinished = _patched_on_indicator_ani_finished
    except Exception as exc:
        NavigationPanel._onIndicatorAniFinished = originals["_onIndicatorAniFinished"]
        if logger is not None:
            logger.warning("qfluent_navigation_patch install failed, rolled back: %s", exc)
        return
    _PATCH_INSTALLED = True
