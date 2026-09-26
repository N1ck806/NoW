"""
Конфигурация бота Nightmare.
Все настройки клана хранятся здесь.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ===== Основные настройки =====
TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "!"
BOT_NAME = "Nightmare"
CLAN_NAME = "Nightmare of Whiners"

# ===== ID сервера =====
GUILD_ID = 1097534186585341952

# ===== ID каналов =====
CHANNEL_LOGS = 1553439253596479559
CHANNEL_WELCOME = 0
CHANNEL_ANNOUNCEMENTS = 0
CHANNEL_LEVELUPS = 0
CHANNEL_GAMES = 0
CHANNEL_EVENTS = 0

# ===== ID ролей =====
ROLE_ADMIN        = 1166119437590614016
ROLE_SMALL_ADMIN  = 1166437756831015051
ROLE_CLAN_ADMIN   = 1194931340580225074
ROLE_MEMBER       = 1166610181044568134
ROLE_RECRUIT      = 1194931640942739486
ROLE_BOT          = 1194933086257950741

# ===== Реакционные роли =====
# Формат: {message_id: {emoji: role_id}}
# Заполняется командой !addrole
REACTION_ROLES = {}

# ===== Экономика =====
CURRENCY_NAME = "монет"
CURRENCY_EMOJI = "💰"
DAILY_REWARD = 100
START_BALANCE = 0

# ===== Активность и уровни =====
XP_PER_MESSAGE = 5
XP_COOLDOWN = 60
LEVEL_REWARD_BASE = 100

# ===== Игры =====
GAME_MIN_BET = 10
GAME_MAX_BET = 10000
COINFLIP_WIN_CHANCE = 0.5
SLOTS_WIN_CHANCE = 0.15
SLOTS_MULTIPLIER = 5
DICE_WIN_CHANCE = 0.4
DICE_MULTIPLIER = 2

# ===== Голосовая активность =====
VOICE_CREATE_CHANNEL = 0          # ID канала-триггера для приватных комнат (0 = выключено)
VOICE_XP_PER_MINUTE = 1           # XP за минуту в войсе
VOICE_COINS_PER_MINUTE = 1        # монет за минуту в войсе

# ===== Цвета для Embed =====
COLOR_MAIN = 0x2b2d31
COLOR_SUCCESS = 0x57f287
COLOR_ERROR = 0xed4245
COLOR_WARNING = 0xfee75c
COLOR_INFO = 0x5865f2