from ncatbot.core import BotClient, GroupMessage, PrivateMessage
from ncatbot.utils import get_log

bot = BotClient()

menu_text = """🤖 QQ机器人功能菜单 🤖
        
📚 禁漫本子下载 (JmComicPlugin)  
• /jm <本子ID> - 下载禁漫本子并发送PDF
• /jmzip <本子ID> - 下载禁漫本子并发送ZIP(失败回退PDF)
• /query <关键词> [数量] - 根据关键词搜索禁漫本子
• /cover <本子ID> - 获取指定本子的封面图片
• /rank [类型] [页码] - 获取禁漫排行榜信息，类型: today, week, month
• 例如: /jm 114514, /query MANA 无修正, /cover 427413, /rank hot 1

🎨 二次元图片 (Lolicon)
• /loli [数量] [标签] - 发送随机二次元图片
• /r18 [数量] [标签] - 发送R18图片(需权限)
• 示例: /loli 3 萝莉、/loli 白丝
"""


# ========== 菜单功能 ==========
@bot.on_group_message()
@bot.on_private_message()
async def on_group_message(msg: GroupMessage):
    if msg.raw_message == "/菜单":
        await msg.reply(text=menu_text)


# ========== 启动 BotClient==========
if __name__ == "__main__":
    bot.run(bt_uin="3849692240", root="2548705244")  # 这里写 Bot 的 QQ 号
