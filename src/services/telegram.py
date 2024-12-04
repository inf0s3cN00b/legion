import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from typing import Optional
from src.config.config import Config
from src.util.logging import Logger
from src.services.notification_service import NotificationService

class TelegramService(NotificationService):
    """Service for interacting with Telegram"""
    _instance: Optional['TelegramService'] = None
    
    def __init__(self):
        self.config = Config()
        self.logger = Logger("TelegramService")
        self.bot_token = self.config.get('telegram', {}).get('bot_token')
        self.chat_id = self.config.get('telegram', {}).get('chat_id')
        
        if not self.bot_token:
            raise ValueError("Telegram bot token not configured")
            
        self.bot = telegram.Bot(token=self.bot_token)
        
    @classmethod
    def get_instance(cls) -> 'TelegramService':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def send_message(self, message: str) -> None:
        """Send a message to the configured chat"""
        if not self.chat_id:
            self.logger.warning("No chat ID configured, skipping message")
            return
            
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {str(e)}")

    async def start_bot(self):
        """Start the Telegram bot"""
        app = Application.builder().token(self.bot_token).build()
        
        # Register handlers
        app.add_handler(CommandHandler("start", self.handle_start))
        app.add_handler(CommandHandler("help", self.handle_help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start the bot
        await app.run_polling()

    async def handle_start(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "👋 Welcome to the Security Program Bot!\n"
            "Use /help to see available commands."
        )

    async def handle_help(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            "Available commands:\n"
            "/list_projects - List all indexed projects\n"
            "/list_assets - List all downloaded assets\n"
            "You can also chat with me about security programs!"
        )

    async def handle_message(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
        """Handle user messages"""
        # Future: Integrate with LLM for chat functionality
        await update.message.reply_text(
            "I understand you! But LLM integration is coming soon..."
        )