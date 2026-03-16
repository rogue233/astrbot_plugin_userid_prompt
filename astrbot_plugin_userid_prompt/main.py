import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event.filter import EventMessageType
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "userid_prompt_injector",
    "YourName",
    "根据用户ID和聊天类型注入不同提示词的插件",
    "1.1.0",
    "https://github.com/YourName/astrbot_plugin_userid_prompt"
)
class UserIdPromptInjector(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)

        # 从配置中读取基本设置
        self.allowed_user_ids = config.get("allowed_user_ids", ["2313375654"])
        self.prompt_for_allowed = config.get("prompt_for_allowed", "")
        self.prompt_for_others = config.get("prompt_for_others", "")

        # 读取私聊专用配置，若不存在则使用群聊的提示词作为默认值
        self.prompt_for_allowed_private = config.get(
            "prompt_for_allowed_private", self.prompt_for_allowed
        )
        self.prompt_for_others_private = config.get(
            "prompt_for_others_private", self.prompt_for_others
        )

        # 处理用户ID列表（转为字符串列表）
        if isinstance(self.allowed_user_ids, str):
            self.allowed_user_ids = [
                uid.strip() for uid in self.allowed_user_ids.split(",") if uid.strip()
            ]
        elif isinstance(self.allowed_user_ids, list):
            self.allowed_user_ids = [
                str(uid).strip() for uid in self.allowed_user_ids if uid
            ]
        else:
            self.allowed_user_ids = []

        # 日志输出
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config",
            "astrbot_plugin_userid_prompt_config.json"
        )
        logger.info("用户ID提示词注入插件已加载")
        logger.info(f"配置文件路径: {config_path}")
        logger.info(f"已配置 {len(self.allowed_user_ids)} 个符合条件的用户")
        logger.info(f"允许的用户ID: {self.allowed_user_ids}")
        logger.info(f"群聊-白名单提示词: {self.prompt_for_allowed}")
        logger.info(f"群聊-其他用户提示词: {self.prompt_for_others}")
        logger.info(f"私聊-白名单提示词: {self.prompt_for_allowed_private}")
        logger.info(f"私聊-其他用户提示词: {self.prompt_for_others_private}")

    @filter.event_message_type(EventMessageType.ALL)
    async def handle_message(self, event: AstrMessageEvent):
        try:
            message_str = event.message_str.strip()
            if not message_str:
                return

            user_id_raw = event.get_sender_id()
            user_id_str = str(user_id_raw)
            user_name = event.get_sender_name() or "未知"

            # ---------- 判断私聊/群聊 ----------
            group_id = event.get_group_id()
            is_private = False

            # 情况1：group_id 为 None（标准私聊）
            if group_id is None:
                is_private = True
            # 情况2：某些平台返回空字符串表示私聊
            elif isinstance(group_id, str) and group_id == '':
                is_private = True
            # 情况3：某些平台返回 0 表示私聊
            elif isinstance(group_id, int) and group_id == 0:
                is_private = True
            # 情况4：尝试从 unified_msg_origin 判断
            elif event.unified_msg_origin and 'private' in event.unified_msg_origin.lower():
                is_private = True
            # 情况5：尝试使用 get_message_type 方法
            elif hasattr(event, 'get_message_type'):
                try:
                    msg_type = event.get_message_type()
                    if msg_type == 'private':
                        is_private = True
                except:
                    pass

            logger.debug(
                f"私聊判断: group_id={group_id!r}, origin={event.unified_msg_origin}, is_private={is_private}"
            )
            # -----------------------------------

            # 根据用户ID和聊天类型选择提示词
            if user_id_str in self.allowed_user_ids:
                if is_private:
                    prompt = self.prompt_for_allowed_private
                else:
                    prompt = self.prompt_for_allowed
            else:
                if is_private:
                    prompt = self.prompt_for_others_private
                else:
                    prompt = self.prompt_for_others

            # 如果私聊提示词为空，则使用群聊的（保持向后兼容）
            if not prompt:
                if user_id_str in self.allowed_user_ids:
                    prompt = self.prompt_for_allowed
                else:
                    prompt = self.prompt_for_others

            # ---------- 调试日志：查看原始消息和选中的提示词 ----------
            original_message = event.message_str
            #logger.info(f"[调试] 原始消息: {original_message}")
            #logger.info(f"[调试] 选中的提示词: {prompt}")
            # --------------------------------------------------------

            # 在原有消息前追加提示词（不覆盖其他插件的修改）
            event.message_str = f"{prompt}\n\n{original_message}"

            # ---------- 调试日志：查看修改后的消息 ----------
            #logger.info(f"[调试] 处理后消息: {event.message_str}")
            # ------------------------------------------------

            logger.info(
                f"用户 {user_id_str} {'符合' if user_id_str in self.allowed_user_ids else '不符合'}条件，"
                f"注入{'私聊' if is_private else '群聊'}提示词"
            )

        except Exception as e:
            logger.error(f"处理消息时发生异常: {e}")

    async def terminate(self):
        logger.info("用户ID提示词注入插件已卸载")