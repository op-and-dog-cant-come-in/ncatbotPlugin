from ncatbot.core.event import GroupMessageEvent, BaseMessageEvent
from ncatbot.plugin_system import NcatBotPlugin, on_group_at, command_registry
from ncatbot.utils import get_log
from openai import OpenAI
import httpx
import asyncio

log = get_log("NekoAssistant")


class NekoAssistant(NcatBotPlugin):
    name = "NekoAssistant"
    version = "1.0.0"
    author = "zhaosiyi"
    description = "群猫娘小助手"

    chat_api_key: str = ""
    video_api_key: str = ""
    client: OpenAI = None
    system_prompt: str = (
        "你是一名智能 QQ 群助理，需要扮演可爱的群猫娘来回复群友的消息。请以温柔可爱的语气进行 100 字以内的回复。用户的消息格式为 群昵称: 消息内容"
    )
    history: list = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_api_key = open("volcengine-api-key.txt", "r").read().strip()
        self.video_api_key = open("volcengine-video-api-key.txt", "r").read().strip()
        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=self.chat_api_key,
        )

    # 调用接口获取 ai 对话回复
    async def chat(self, message: str) -> str:
        # 创建一个对话请求
        response = self.client.responses.create(
            model="deepseek-v3-2-251201",
            input=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.8,
            stream=False,
        )

        # 提取回复内容
        res = response.output[0].content[0].text
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": res})

        # 仅保留最新的 15 轮对话
        self.history = self.history[-30:]

        return res

    # 在被 @ 且回复不为空时，调用 ai 对话接口
    @on_group_at
    async def on_group_at(self, msg: GroupMessageEvent):
        text = msg.message.concatenate_text().strip()
        await msg.reply(await self.chat(text))

    @command_registry.command("video", description="生成视频")
    async def generate_video(self, event: BaseMessageEvent, duration: int, prompt: str):
        """根据提示词生成视频，未来考虑支持参考图"""
        try:
            # 构建视频生成请求
            video_api_url = (
                "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
            )
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.video_api_key}",
            }
            data = {
                "model": "doubao-seedance-1-5-pro-251215",
                "content": [{"type": "text", "text": prompt}],
                "duration": duration,
            }

            # 发送视频生成请求
            async with httpx.AsyncClient() as client:
                response = await client.post(video_api_url, headers=headers, json=data)
                response.raise_for_status()
                task_id = response.json()["id"]

            # 通知用户任务已开始
            await event.reply(f"视频生成任务已开始，任务ID: {task_id}")

            # 轮询任务状态
            polling_url = f"https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}"
            max_retries = 30  # 最多轮询30次（约30分钟）
            retry_count = 0

            while retry_count < max_retries:
                await asyncio.sleep(60)  # 每隔1分钟轮询一次
                retry_count += 1

                async with httpx.AsyncClient() as client:
                    status_response = await client.get(polling_url, headers=headers)
                    status_response.raise_for_status()
                    status_data = status_response.json()

                if status_data.get("status") == "succeeded":
                    video_url = status_data.get("content", {}).get("video_url")
                    if video_url:
                        # 下载视频文件
                        await event.reply("视频生成成功，正在下载视频...")
                        file_name = f"video_{task_id}.mp4"
                        file_path = f"./temp/{file_name}"

                        # 创建临时目录
                        import os

                        os.makedirs("./temp", exist_ok=True)

                        # 下载视频
                        async with httpx.AsyncClient() as client:
                            video_response = await client.get(video_url)
                            video_response.raise_for_status()
                            with open(file_path, "wb") as f:
                                f.write(video_response.content)

                        # 发送文件
                        await self.api.send_group_file(
                            group_id=event.group_id,
                            file=file_path,
                            name=file_name,
                        )

                        # 清理临时文件
                        os.remove(file_path)
                    else:
                        await event.reply("视频生成成功，但未获取到视频链接")
                    return
                elif status_data.get("status") in ["failed", "cancelled"]:
                    await event.reply(
                        f"视频生成失败，状态：{status_data.get('status')}"
                    )
                    return

            # 轮询超时
            await event.reply("视频生成超时，请稍后重试")

        except Exception as e:
            log.error(f"生成视频时出错: {str(e)}")
            await event.reply(f"生成视频时出错: {str(e)}")
