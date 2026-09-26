"""
Проверки прав для команд Nightmare.
"""

import discord
from discord.ext import commands
import config


def _has_role(member: discord.Member, role_ids: set) -> bool:
    """Проверяет наличие хотя бы одной роли из списка."""
    return bool(role_ids & {role.id for role in member.roles})


def is_admin():
    """Высший админ: Администратор сервера или роль ROLE_ADMIN."""
    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member):
            return False
        if ctx.author.guild_permissions.administrator:
            return True
        if config.ROLE_ADMIN and config.ROLE_ADMIN in {r.id for r in ctx.author.roles}:
            return True
        raise commands.MissingPermissions(["admin"])
    return commands.check(predicate)


def is_staff():
    """Персонал: Администратор, Администратор клана, Маленький админ."""
    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member):
            return False
        if ctx.author.guild_permissions.administrator:
            return True

        staff_roles = {
            rid for rid in (
                config.ROLE_ADMIN,
                config.ROLE_CLAN_ADMIN,
                config.ROLE_SMALL_ADMIN,
            ) if rid
        }
        if _has_role(ctx.author, staff_roles):
            return True

        raise commands.MissingPermissions(["staff"])
    return commands.check(predicate)


def is_clan_admin():
    """Персонал клана (синоним is_staff, оставлен для совместимости)."""
    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member):
            return False
        if ctx.author.guild_permissions.administrator:
            return True

        admin_roles = {
            rid for rid in (
                config.ROLE_ADMIN,
                config.ROLE_CLAN_ADMIN,
                config.ROLE_SMALL_ADMIN,
            ) if rid
        }
        if _has_role(ctx.author, admin_roles):
            return True

        raise commands.MissingPermissions(["clan_admin"])
    return commands.check(predicate)


def is_moderator():
    """Модератор: любой из staff-ролей + модератор (если добавишь)."""
    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member):
            return False
        if ctx.author.guild_permissions.administrator:
            return True

        mod_roles = {
            rid for rid in (
                config.ROLE_ADMIN,
                config.ROLE_CLAN_ADMIN,
                config.ROLE_SMALL_ADMIN,
            ) if rid
        }
        if _has_role(ctx.author, mod_roles):
            return True

        # Discord-права на модерацию
        perms = ctx.author.guild_permissions
        if perms.kick_members or perms.ban_members or perms.manage_messages:
            return True

        raise commands.MissingPermissions(["moderator"])
    return commands.check(predicate)


def is_owner():
    """Владелец сервера."""
    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member):
            return False
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        raise commands.MissingPermissions(["owner"])
    return commands.check(predicate)


def has_role(*role_ids):
    """Проверка на конкретные роли."""
    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member):
            return False
        if ctx.author.guild_permissions.administrator:
            return True
        if _has_role(ctx.author, set(role_ids)):
            return True
        raise commands.MissingPermissions(["role"])
    return commands.check(predicate)


def is_member():
    """Участник клана (роль ROLE_MEMBER или ROLE_RECRUIT)."""
    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member):
            return False
        member_roles = {
            rid for rid in (
                config.ROLE_MEMBER,
                config.ROLE_RECRUIT,
            ) if rid
        }
        if _has_role(ctx.author, member_roles):
            return True
        # Админы автоматически допущены
        if ctx.author.guild_permissions.administrator:
            return True
        raise commands.MissingPermissions(["member"])
    return commands.check(predicate)