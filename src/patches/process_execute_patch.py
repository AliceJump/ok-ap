from __future__ import annotations

_PATCH_INSTALLED = False
_original_execute = None


def _execute_fixed(game_cmd: str, arguments=None, start_method=None):
    """ok.util.process.execute 的修复版(见 install_process_execute_patch)。"""
    import ok.util.process as process_mod

    if start_method is None:
        start_method = process_mod.WINDOWS_START_METHOD_START
    if not game_cmd:
        return None
    if "://" in game_cmd:
        try:
            process_mod.logger.info(f"try execute url {game_cmd}")
            process_mod.os.startfile(game_cmd)
            return True
        except Exception as e:
            process_mod.logger.error("execute error", e)
        return None
    game_path = process_mod.get_path(game_cmd)
    if not process_mod.os.path.exists(game_path):
        process_mod.logger.error(f"execute error path not exist {game_path}")
        return None
    try:
        process_mod.logger.info(f"try execute {game_cmd} {arguments} with {start_method}")
        working_dir = process_mod.os.path.dirname(game_path)
        if start_method == process_mod.WINDOWS_START_METHOD_OS_STARTFILE:
            _, args_part = process_mod._split_game_command(game_cmd, game_path, arguments)
            process_mod.os.startfile(game_path, "open", args_part or "", working_dir, 5)
            return True
        cmd = process_mod._build_windows_start_command(game_cmd, game_path, arguments)
        process_mod.subprocess.Popen(
            cmd,
            cwd=working_dir,
            shell=True,
            stdout=process_mod.subprocess.DEVNULL,
            stderr=process_mod.subprocess.DEVNULL,
            creationflags=getattr(process_mod.subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        return True
    except Exception as e:
        process_mod.logger.error("execute error", e)
        return None


def install_process_execute_patch():
    """Fix ok.util.process.execute: DEVNULL stdout/stderr to prevent pipe buffer
    blocking, and pass empty string instead of None to os.startfile."""
    global _PATCH_INSTALLED, _original_execute
    if _PATCH_INSTALLED:
        return
    try:
        import ok.util.process as process_mod
    except Exception:
        return
    if _original_execute is None:
        _original_execute = process_mod.execute
    process_mod.execute = _execute_fixed
    _PATCH_INSTALLED = True
