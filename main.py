import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event.filter import EventMessageType
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "userid_prompt_injector", 
    "YourName", 
    "根据用户ID注入不同提示词的插件", 
    "1.0.2",
    "https://github.com/YourName/astrbot_plugin_userid_prompt"  # 可选，你的仓库地址
)
class UserIdPromptInjector(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        
        # config 是AstrBot自动从配置文件传入的
        # 配置文件路径: data/config/astrbot_plugin_userid_prompt_config.json
        
        # 从配置中读取设置
        self.allowed_user_ids = config.get("allowed_user_ids", ["123456"])
        self.prompt_for_allowed = config.get("prompt_for_allowed", "")
        self.prompt_for_others = config.get("prompt_for_others", "")
        
        # 确保用户ID列表为字符串列表
        if isinstance(self.allowed_user_ids, str):
            # 如果是字符串，按逗号分割
            self.allowed_user_ids = [uid.strip() for uid in self.allowed_user_ids.split(",") if uid.strip()]
        elif isinstance(self.allowed_user_ids, list):
            # 如果是列表，确保所有元素都是字符串
            self.allowed_user_ids = [str(uid).strip() for uid in self.allowed_user_ids if uid]
        else:
            self.allowed_user_ids = []
        
        # 获取配置文件路径（仅用于日志显示）
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config",
            "astrbot_plugin_userid_prompt_config.json"
        )
        
        logger.info(f"用户ID提示词注入插件已加载")
        logger.info(f"配置文件路径: {config_path}")
        logger.info(f"已配置 {len(self.allowed_user_ids)} 个符合条件的用户")
        logger.info(f"允许的用户ID: {self.allowed_user_ids}")
        logger.info(f"特殊提示词: {self.prompt_for_allowed[:50]}..." if self.prompt_for_allowed else "特殊提示词: 未配置")
        logger.info(f"普通提示词: {self.prompt_for_others[:50]}..." if self.prompt_for_others else "普通提示词: 未配置")

    @filter.event_message_type(EventMessageType.ALL)
    async def handle_message(self, event: AstrMessageEvent):
        """
        处理所有消息，根据用户ID注入不同提示词
        """
        try:
            message_str = event.message_str.strip()
            if not message_str:
                return

            user_id_raw = event.get_sender_id()
            user_id_str = str(user_id_raw)
            user_name = event.get_sender_name() or "未知"

            logger.debug(f"收到来自用户 {user_name}(ID: {user_id_str}) 的消息: {message_str}")

            # 检查是否有配置提示词
            if not self.prompt_for_allowed or not self.prompt_for_others:
                logger.warning("提示词未配置完整，跳过注入")
                return

            if user_id_str in self.allowed_user_ids:
                new_message = f"{self.prompt_for_allowed}\n\n用户消息: {message_str}"
                logger.info(f"用户 {user_id_str} 符合条件，已注入特殊提示词")
            else:
                new_message = f"{self.prompt_for_others}\n\n用户消息: {message_str}"
                logger.info(f"用户 {user_id_str} 不符合条件，已注入普通提示词")

            event.message_str = new_message
            # 不yield，让消息继续流向AI处理器

        except Exception as e:
            logger.error(f"处理消息时发生异常: {e}，事件: {event}")

    async def terminate(self):
        logger.info("用户ID提示词注入插件已卸载")