# ok-ap 项目文档

面向《蓝色星原：旅谣》（Azur Promilia）的游戏自动化项目，基于 [ok-script](https://ok-script.com/) 开发。

## 快速导航

- [从源码运行](dev/QUICKSTART.md)
- [开发指南](dev/DEVELOPMENT.md)

## 项目结构

```
├── main.py / main_debug.py     入口（Release / Debug）
├── src/
│   ├── config.py               ok-script 应用配置与任务注册
│   ├── globals.py              全局单例
│   ├── icons.py                图标（默认复用 FluentIcon）
│   ├── core/
│   │   ├── BaseGameTask.py     任务基类
│   │   ├── config_migration.py 配置键迁移
│   │   └── global_config_store.py 全局配置存储
│   ├── tasks/
│   │   ├── onetime/            一次性任务
│   │   ├── trigger/            触发式任务
│   │   ├── test/               测试任务
│   │   └── account/            账号作用域配置存储
│   ├── gui/                    自定义 Tab（全局配置 / 账号配置）
│   ├── interaction/            游戏交互（窗口 / 键鼠）
│   ├── patches/                启动补丁
│   └── data/
│       ├── FeatureList.py      模板匹配特征枚举
│       └── lang/               lang JSON 读取器
├── assets/lang/                OCR 语言 JSON
├── i18n/*/LC_MESSAGES/ok.po    6 种语言 gettext 目录
├── tests/                      unittest 测试
├── scripts/ tools/             通用工具脚本
└── .github/workflows/          CI（build / docs / auto-release）
```