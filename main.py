import asyncio

from ncatbot.core import BotClient, GroupMessageEvent
from ncatbot.plugin_system import on_group_at, command_registry
from ncatbot.utils import get_log, status

bot = BotClient()
log = get_log()


# ========== 菜单功能 ==========
@on_group_at
async def show_menu(msg: GroupMessageEvent):
    """
    处理群聊中 @ 机器人的事件
    """
    text = msg.message.concatenate_text()
    if text.replace(" ", "") != "":
        return
    log.info(f"机器人被用户{msg.sender.user_id}@了")
    commands = command_registry.get_all_commands()
    log_contents = ["\n🤖 QQ机器人功能菜单 🤖"]  # 用于收集日志内容
    for value in commands.values():
        log.info(f"commands:{value.__dict__}")
        log_content = f"• /{value.name} "
        for index, types in enumerate(value.args_types):
            try:
                element = value.params[index]
            except IndexError:
                element = None
            if element is not None:
                log_content += f"[{element.description}]"
            log_content += f"<{types.__name__}> "
        log_content += f"- {value.description}"
        log_contents.append(log_content)

    # 将所有日志内容拼接为一个字符串
    result = "\n".join(log_contents)
    message_id = await  msg.reply(result)
    # 等待 5 秒
    # await delete_after_seconds(message_id)


async def delete_after_seconds(message_id, seconds=5):
    """几秒后撤回消息"""
    await asyncio.sleep(seconds)
    await status.global_api.delete_msg(message_id)


# ========== 启动 BotClient==========
if __name__ == "__main__":
    bot.run(bt_uin="3849692240", root="2548705244")  # 这里写 Bot 的 QQ 号
