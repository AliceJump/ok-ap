from __future__ import annotations

_PATCH_INSTALLED = False


def install_startup_patches():
    global _PATCH_INSTALLED
    if _PATCH_INSTALLED:
        return

    from src.patches.i18n_collection_patch import install_i18n_collection_patch
    from src.patches.ocr_text_fix_patch import install_ocr_text_fix_patch
    from src.patches.overlay_dpi_patch import install_overlay_dpi_patch
    from src.patches.screenshot_sidecar_patch import install_screenshot_sidecar_patch
    from src.patches.schedule_task_name_patch import install_schedule_task_name_patch
    from src.patches.startup_window_patch import install_startup_window_patch
    from src.patches.task_config_lock_patch import install_task_config_lock_patch

    install_i18n_collection_patch()
    install_ocr_text_fix_patch()
    install_overlay_dpi_patch()
    install_screenshot_sidecar_patch()
    install_schedule_task_name_patch()
    install_startup_window_patch()
    install_task_config_lock_patch()
    _PATCH_INSTALLED = True