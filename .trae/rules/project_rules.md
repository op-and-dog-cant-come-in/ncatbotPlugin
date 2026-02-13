# 项目概述

这是一个基于 NcatBot 框架的多功能 QQ 机器人项目，使用 Python 3.12+ 开发。

# 技术栈

- Python 3.9+
- 使用 NcatBot 代理 QQ 客户端实现机器人操作，不使用 QQ 官方的机器人功能
- 使用 uv 管理 python 依赖

## 代码规范

### Python 代码风格

- 遵循 PEP 8 编码规范
- 使用 4 空格缩进
- 行长度限制为 120 字符
- 使用类型注解
- 函数和类使用 docstring 文档

### 命名规范

- 文件名: 小写，使用下划线分隔（如 `main.py`, `test_plugin.py`）
- 类名: 大驼峰命名（如 `BotClient`, `GroupMessageEvent`）
- 函数名: 小写，使用下划线分隔（如 `show_menu`, `delete_after_seconds`）
- 变量名: 小写，使用下划线分隔
- 常量: 全大写，使用下划线分隔

### 插件开发规范

- 每个插件放在 `plugins/` 目录下的独立文件夹中
- 插件必须包含 `__init__.py` 和 `main.py` 文件
- 插件应该有自己的 `requirements.txt` 和 `README.md`
- 使用装饰器注册命令（如 `@on_group_at`, `@command`）

## 项目结构

```
ncatbotPlugin/
├── main.py                 # 主入口文件
├── requirements.txt        # 项目依赖
├── plugins/               # 插件目录
│   ├── PluginName/        # 单个插件
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── README.md
│   └── ...
└── .trae/
    └── rules/
        └── project_rules.md  # 本文件
```

## 开发命令

### 依赖管理

```bash
# 使用 uv（推荐）
uv venv                    # 创建虚拟环境
uv pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --upgrade
```

### 运行项目

```bash
# 使用 uv
uv run main.py
```
