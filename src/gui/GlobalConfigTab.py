from qfluentwidgets import FluentIcon, NavigationItemPosition

from ok.gui.tasks.ConfigCard import ConfigCard
from ok.gui.widget.CustomTab import CustomTab

from src.core.global_config_store import get_all_visible_configs


GLOBAL_CONFIG_GROUPS = {
    "基础配置": ["Ensure Main Once Action Sleep"],
    "键位配置": ["Game Hotkey Config"],
}


class GlobalConfigTab(CustomTab):
    @property
    def name(self):
        # MainWindow 会对 tab 的 name 统一调用 self.app.tr(name)，
        # 这里必须返回源 key（"全局配置"）而非已翻译文本。
        return "全局配置"

    @property
    def position(self):
        return NavigationItemPosition.TOP

    @property
    def add_after_default_tabs(self):
        return False

    @property
    def icon(self):
        return FluentIcon.SETTING

    def showEvent(self, event):
        super().showEvent(event)
        if self.vBoxLayout.count() == 0:
            self._build_cards()

    def _build_cards(self):
        visible_configs = {
            name: (config, option)
            for name, config, option in get_all_visible_configs()
        }
        shown = set()
        for group_name, config_names in GLOBAL_CONFIG_GROUPS.items():
            for config_name in config_names:
                config_and_option = visible_configs.get(config_name)
                if config_and_option is None:
                    continue
                config, option = config_and_option
                shown.add(config_name)
                card = ConfigCard(
                    None,
                    group_name,
                    config,
                    option.description,
                    option.default_config,
                    option.config_description,
                    option.config_type,
                    option.icon,
                )
                self.add_widget(card)

        for config_name, (config, option) in visible_configs.items():
            if config_name in shown:
                continue
            card = ConfigCard(
                None,
                "其他配置",
                config,
                option.description,
                option.default_config,
                option.config_description,
                option.config_type,
                option.icon,
            )
            self.add_widget(card)