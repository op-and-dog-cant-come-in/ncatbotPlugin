from ncatbot.core.event import BaseMessageEvent
from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry
from ncatbot.plugin_system import param
from ncatbot.utils import get_log

log = get_log("TestPlugin")


class TestPlugin(NcatBotPlugin):
    name = "TestPlugin"
    version = "1.0.0"
    author = "wyz"
    description = "测试bot插件子类"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def on_load(self):
        # 可留空，保持轻量
        log.info(f"{self.name} 插件已加载")

    @command_registry.command("test", aliases=["测试"], description="测试接口", prefixes=["@on_group_at"])
    @param(name="input_str", default="你好", help="图片标签")
    async def test_cmd(self, event: BaseMessageEvent, input_str: str = ""):
        commands = command_registry.get_all_commands()
        log_contents = []  # 用于收集日志内容
        for value in commands.values():
            log_content = f"commands:{value.__dict__}"
            log_contents.append(log_content)

        # 将所有日志内容拼接为一个字符串
        result = "\n".join(log_contents)
        await  event.reply(result)
