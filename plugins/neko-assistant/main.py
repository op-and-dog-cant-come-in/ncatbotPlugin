from ncatbot.core.event import GroupMessageEvent, BaseMessageEvent
from ncatbot.plugin_system import NcatBotPlugin, on_group_at, command_registry
from ncatbot.utils import get_log
import httpx
import asyncio
import json
import pickle
import os
import pprint

log = get_log("NekoAssistant")


class NekoAssistant(NcatBotPlugin):
    name = "NekoAssistant"
    version = "1.0.0"
    author = "zhaosiyi"
    description = "群猫娘小助手"

    chat_api_key: str = ""
    video_api_key: str = ""
    system_prompt: str = ""

    # 保存最近 15 条的历史记录
    history: list = []

    # 按用户 id 记录用户偏好，
    # key 为 user_id，value 为偏好内容的字符串
    preferences = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 读取系统提示词
        script_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        prompt_file = os.path.join(script_dir, ".system-prompts.md")

        if os.path.exists(prompt_file):
            with open(prompt_file, "r", encoding="utf-8") as f:
                self.system_prompt = f.read().strip()
        else:
            log.warning(f"系统提示词文件 {prompt_file} 不存在，使用默认提示词")
            self.system_prompt = "你需要扮演温柔可爱的群猫娘来回复 QQ 群友的消息。"

        self.chat_api_key = open("volcengine-api-key.txt", "r").read().strip()
        self.video_api_key = open("volcengine-video-api-key.txt", "r").read().strip()

        # 读取用户偏好
        if os.path.exists("preferences.pkl"):
            with open("preferences.pkl", "rb") as f:
                self.preferences = pickle.load(f)

    # 调用接口获取 ai 对话回复
    async def chat(self, message: str) -> str:
        url = "https://ark.cn-beijing.volces.com/api/v3/responses"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.chat_api_key}",
        }
        data = {
            "model": "deepseek-v3-2-251201",
            "input": [
                {
                    "role": "system",
                    "content": f"{self.system_prompt}\n按 user_id 记录的群员偏好如下：\n{self.preferences}",
                },
                {"role": "user", "content": message},
            ],
            "temperature": 0.8,
            "stream": False,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            response_data = response.json()

        res_text = response_data["output"][0]["content"][0]["text"]

        ## 尝试将回复内容解析为 JSON
        try:
            output = json.loads(res_text)
        except json.JSONDecodeError:
            log.error(f"解析 JSON 失败: {res_text}")
            output = {"text": res_text, "at": False}

        # 仅保留最新的 15 轮对话
        self.history = self.history[-30:]

        result_text = output.get("text", "")
        result_at = output.get("at_group_user", False)
        result_preferences = output.get("preferences")

        if result_preferences:
            if result_preferences["override"]:
                self.preferences[result_preferences["id"]] = result_preferences[
                    "content"
                ]
            else:
                if result_preferences["id"] not in self.preferences:
                    self.preferences[result_preferences["id"]] = ""

                self.preferences[result_preferences["id"]] += result_preferences[
                    "content"
                ]

        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": result_text})

        with open("preferences.pkl", "wb") as f:
            pickle.dump(self.preferences, f)

        if result_at:
            result_text = f" {result_text}"

        return {
            "text": result_text,
            "at": result_at,
        }

    # 在被 @ 且回复不为空时，调用 ai 对话接口
    @on_group_at
    async def on_group_at(self, msg: GroupMessageEvent):
        text = msg.message.concatenate_text().strip()
        res = await self.chat(f"{msg.sender.nickname}({msg.user_id}): {text}")

        await self.api.post_group_msg(
            group_id=msg.group_id,
            text=res.get("text", ""),
            at=res.get("at", False),
        )

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
                        await event.reply("视频生成成功，正在下载视频...", at=False)
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

    @command_registry.command("preferences")
    async def handle_preferences(self, event: BaseMessageEvent, action: str = "get"):
        """设置或查询用户偏好"""
        if action == "get":
            await event.reply(
                f"当前记录的偏好数据如下: {pprint.pformat(self.preferences)}",
                at=False,
            )

        elif action == "clear":
            self.preferences = ""
            with open("preferences.txt", "w") as f:
                f.write("")
            await event.reply("用户偏好已清空", at=False)
