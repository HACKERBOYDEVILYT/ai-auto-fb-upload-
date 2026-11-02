#!/usr/bin/env python3
"""
Telegram Bot integration for sending results
"""

import telebot
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramBot:
    """Sends messages to Telegram"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.bot = telebot.TeleBot(token)
        logger.info("Telegram bot initialized")
    
    async def send_message(self, message: str):
        """Send message to Telegram"""
        
        try:
            self.bot.send_message(
                self.chat_id,
                message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            logger.debug("Message sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
    
    async def send_photo(self, photo_path: str, caption: str = None):
        """Send photo to Telegram"""
        
        try:
            with open(photo_path, 'rb') as f:
                self.bot.send_photo(
                    self.chat_id,
                    f,
                    caption=caption
                )
        except Exception as e:
            logger.error(f"Failed to send photo: {str(e)}")
    
    async def send_document(self, doc_path: str, caption: str = None):
        """Send document to Telegram"""
        
        try:
            with open(doc_path, 'rb') as f:
                self.bot.send_document(
                    self.chat_id,
                    f,
                    caption=caption
                )
        except Exception as e:
            logger.error(f"Failed to send document: {str(e)}")
