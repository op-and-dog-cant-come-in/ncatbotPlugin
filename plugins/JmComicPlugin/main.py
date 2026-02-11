import os
import zipfile
import asyncio

import jmcomic
from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry
from ncatbot.core.event import BaseMessageEvent
from ncatbot.core import GroupMessage, PrivateMessage
from ncatbot.core import MessageChain, Image


class JmComicPlugin(NcatBotPlugin):
    name = "JmComicPlugin"
    version = "0.0.1"
    author = "FunEnn"
    description = "禁漫本子下载插件，支持通过/jm命令下载本子并发送PDF文件"

    async def on_load(self):
        # 获取项目根目录
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../")
        )
        self.base_dir = os.path.join(project_root, "pdf")
        # 创建封面临时目录
        self.cover_dir = os.path.join(project_root, "cover")
        # jmcomic 配置
        config_path = os.path.join(os.path.dirname(__file__), "option.yml")
        self.jm_option = jmcomic.JmOption.from_file(config_path)

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.cover_dir, exist_ok=True)

    def _pdf_path(self, album_id: str) -> str:
        return os.path.join(self.base_dir, f"{album_id}.pdf")

    def _zip_path(self, album_id: str) -> str:
        return os.path.join(self.base_dir, f"{album_id}.zip")

    async def _ensure_pdf(self, event: BaseMessageEvent, album_id: str) -> str | None:
        pdf_path = self._pdf_path(album_id)

        if os.path.exists(pdf_path):
            return pdf_path

        await event.reply(f"开始下载本子 {album_id}，请稍候...")
        self.jm_option.download_album([album_id])

        if os.path.exists(pdf_path):
            return pdf_path

        return None

    def _build_zip_from_pdf(self, album_id: str, pdf_path: str) -> str:
        zip_path = self._zip_path(album_id)
        pdf_name_in_zip = os.path.basename(pdf_path)

        with zipfile.ZipFile(
            zip_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as zf:
            zf.write(pdf_path, arcname=pdf_name_in_zip)

        return zip_path

    @command_registry.command("jm", description="下载禁漫本子并发送PDF文件")
    async def jm_download_cmd(self, event: BaseMessageEvent, album_id: str):
        """下载禁漫本子命令"""
        try:
            if not album_id.isdigit():
                await event.reply("本子ID必须是数字，例如: /jm 422866")
                return

            pdf_path = await self._ensure_pdf(event, album_id)
            if not pdf_path:
                await event.reply("未找到 PDF 文件，可能下载失败。")
                return

            await self._send_file(event, pdf_path)
        except Exception as e:
            await event.reply(f"下载过程中发生错误: {str(e)}")

    @command_registry.command(
        "jmzip", description="下载禁漫本子并发送ZIP压缩包（失败则回退发送PDF）"
    )
    async def jmzip_download_cmd(self, event: BaseMessageEvent, album_id: str):
        """下载禁漫本子并发送 ZIP"""
        try:
            if not album_id.isdigit():
                await event.reply("本子ID必须是数字，例如: /jmzip 422866")
                return

            zip_path = self._zip_path(album_id)

            if not os.path.exists(zip_path):
                pdf_path = await self._ensure_pdf(event, album_id)
                if not pdf_path:
                    await event.reply("未找到 PDF 文件，可能下载失败。")
                    return

                await event.reply("开始打包本子 {album_id} ，请稍候...")
                zip_path = self._build_zip_from_pdf(album_id, pdf_path)

            try:
                await self._send_file(event, zip_path)
            except Exception as e:
                await event.reply(f"ZIP发送失败，尝试发送PDF... ({str(e)})")
                pdf_path = self._pdf_path(album_id)
                if os.path.exists(pdf_path):
                    await self._send_file(event, pdf_path)
                else:
                    await event.reply("PDF 文件不存在，无法回退发送。")
        except Exception as e:
            await event.reply(f"jmzip 执行过程中发生错误: {str(e)}")

    async def _send_file(self, event: BaseMessageEvent, file_path: str):
        """发送文件（PDF/ZIP）"""
        file_name = os.path.basename(file_path)

        if isinstance(event, PrivateMessage):
            await self.api.send_private_file(
                user_id=event.user_id,
                file=file_path,
                name=file_name,
            )
        elif isinstance(event, GroupMessage):
            await self.api.send_group_file(
                group_id=event.group_id,
                file=file_path,
                name=file_name,
            )
        else:
            await event.reply(f"文件已准备就绪: {file_name}")

    @command_registry.command("query", description="根据关键词搜索禁漫本子")
    async def jm_query_cmd(
        self, event: BaseMessageEvent, search_query: str, amount: int = 20
    ):
        """搜索禁漫本子命令"""
        try:
            if not search_query:
                await event.reply(
                    "请提供搜索关键词，例如: /query MANA 无修正 或 /query 427413"
                )
                return

            # 创建JmClient实例
            client = self.jm_option.new_jm_client()

            await event.reply(f"正在搜索关键词: {search_query}，请稍候...")

            # 搜索漫画
            page = client.search_site(search_query=search_query, page=1)

            if page.total == 0:
                await event.reply(f"未找到与 '{search_query}' 相关的本子")
                return

            # 构建搜索结果消息
            result_msg = f"搜索结果 (共{page.total}个本子，当前第1页):\n\n"

            # 只显示前10个结果
            count = 0

            for album_id, title in page:
                if count >= amount:
                    break
                result_msg += f"[{album_id}]: {title}\n"
                count += 1

            if page.total > amount:
                result_msg += f"\n... 还有 {page.total - amount} 个结果未显示"

            await event.reply(result_msg)

        except Exception as e:
            await event.reply(f"搜索过程中发生错误: {str(e)}")

    @command_registry.command("cover", description="获取指定本子的封面图片")
    async def jm_cover_cmd(self, event: BaseMessageEvent, album_ids_str: str):
        """获取指定album_id的封面图片命令，支持多个本子ID，用逗号或空格分隔"""
        try:
            if not album_ids_str:
                await event.reply(
                    "请提供有效的本子ID，例如: /cover 427413 或 /cover 114514,233214"
                )
                return

            # 按逗号（中英文）和空格分割字符串，得到id列表
            album_ids = (
                album_ids_str.replace("，", " ")
                .replace("、", " ")
                .replace(",", " ")
                .split(" ")
            )

            # 过滤空字符串
            album_ids = [id.strip() for id in album_ids if id.strip()]

            if not album_ids:
                await event.reply(
                    "请提供有效的本子ID，例如: /cover 427413 或 /cover 114514,233214"
                )
                return

            await event.reply(f"正在获取 {len(album_ids)} 个本子的封面图片，请稍候...")

            # 存储成功下载的封面图片路径
            successful_covers = []

            # 处理每个album_id
            for album_id in album_ids:
                if not album_id or not album_id.isdigit():
                    await event.reply(f"本子ID {album_id} 无效，请提供数字ID")
                    continue

                # 为每个封面下载创建独立的JmClient实例
                client = self.jm_option.new_jm_client()

                # 下载封面，添加自动重试3次
                cover_path = os.path.join(self.cover_dir, f"{album_id}.jpg")
                retry_count = 6
                success = False

                for i in range(retry_count):
                    try:
                        client.download_album_cover(album_id, cover_path, "_3x4")
                        success = True
                        break
                    except Exception as e:
                        continue

                if success:
                    # 将成功的封面路径添加到列表
                    successful_covers.append(cover_path)

            # 所有本子处理完毕后，批量发送成功的封面图片
            if successful_covers:
                # 创建包含所有图片的MessageChain
                images = [Image(cover_path) for cover_path in successful_covers]
                image_chain = MessageChain(images)
                # 一次性发送所有图片
                id = await event.reply(image_chain)
                print(id)
                await asyncio.sleep(15)
                await self.api.delete_msg(id)

        except Exception as e:
            await event.reply(f"执行过程中发生错误: {str(e)}")

    @command_registry.command("rank", description="获取禁漫排行榜信息")
    async def jm_rank_cmd(
        self, event: BaseMessageEvent, rank_type: str = "month", page: int = 1
    ):
        """获取禁漫排行榜信息命令"""
        try:
            # 验证参数
            if page < 1:
                await event.reply("页码必须大于0")
                return

            # 验证排行榜类型
            rank_type = rank_type.lower()

            # 创建JmClient实例
            client = self.jm_option.new_jm_client()

            await event.reply(f"正在获取{rank_type}排行榜第{page}页，请稍候...")

            if rank_type == "today":
                rank_page = client.day_ranking(page)
                rank_name = "日排行"
            elif rank_type == "month":
                rank_page = client.month_ranking(page)
                rank_name = "月排行"
            elif rank_type == "week":
                rank_page = client.week_ranking(page)
                rank_name = "周排行"
            else:
                await event.reply(
                    f"无效的排行榜类型，请选择: today, week, month 之一，当前输入 {rank_type}"
                )
                return

            if rank_page.total == 0:
                await event.reply(f"未找到{rank_name}数据")
                return

            # 构建排行榜消息
            result_msg = (
                f"禁漫{rank_name} (第{page}页，共{rank_page.page_count}页):\n\n"
            )

            # 显示排行榜前10个结果
            count = 0
            for album_id, title in rank_page:
                if count >= 10:
                    break
                result_msg += f"{count + 1}. [{album_id}]: {title}\n"
                count += 1

            # 发送消息
            await event.reply(result_msg)

        except Exception as e:
            await event.reply(f"获取排行榜过程中发生错误: {str(e)}")
