# TOSS-Intro-Bot - Discord Bot
# Copyright (C) 2020 - 2021 Dylan Prins
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see <https://www.gnu.org/licenses/gpl-3.0.txt>.

# You may contact me at toss@sinelservers.xyz

import os
from typing import Union
from discord.ext import commands
from discord.ext.commands import errors
from discord.errors import NotFound
from discord import AllowedMentions, Message, RawMessageDeleteEvent, RawBulkMessageDeleteEvent, \
    Embed, Activity, ActivityType, Member, TextChannel, File, utils
from database.history import History


bot = commands.Bot(command_prefix="i! ", allowed_mentions=AllowedMentions(roles=False, everyone=False))


@bot.event
async def on_ready():
    joyte = await bot.fetch_user(246862123328733186)
    bot.joy_url = joyte.avatar_url

    await bot.change_presence(activity=Activity(type=ActivityType.watching, name="over TOSS's Introductions"))
    print(f"Logged in as the bot ({bot.user})!")


@bot.event
async def on_command_error(ctx: Member, error: errors):
    if isinstance(error, errors.MemberNotFound):
        await ctx.send("That's not a valid member!")
        return
    if isinstance(error, errors.CommandNotFound):
        return
    raise error


@bot.event
async def on_message(message: Message):
    if bot.user in message.mentions:
        await message.channel.send("Hey, my prefix is `i! `!")
        return

    if message.author.bot:
        return

    history = History(message.guild.id)

    if history.get_intro_channel() != message.channel.id:
        await bot.process_commands(message)
        return

    history.add(message.author.id, message.id)

    role = utils.get(message.guild.roles, name="Staff")
    if role in message.author.roles:
        return

    total = history.get(message.author.id)
    if total == 1:
        return

    message_links_formatted = ""
    # noinspection PyTypeChecker
    for index, message_id in enumerate(history.get(message.author.id, ids=True)):
        message_links_formatted += f"[{index+1}: {message_id}](https://discord.com/channels/{message.guild.id}/{history.get_intro_channel()}/{message_id})\n"

    if len(message_links_formatted) > 5000:
        with open(f"./{message.author.id}.txt", "w+") as fp:
            fp.write(message_links_formatted)

        message_links_formatted = f"[{total}: {message.id}](https://discord.com/channels/{message.guild.id}/{history.get_intro_channel()}/{message.id})\nRest is in file"

    e = Embed(colour=0x00FF00)
    e.title = "Messages Exceeded"
    e.description = f"`{message.author}` **|** `{message.author.id}`\nThis user has sent `{total}` messages in <#{message.channel.id}>"
    e.add_field(name="Message links", value=message_links_formatted, inline=False)
    e.set_thumbnail(url=message.author.avatar_url)
    e.timestamp = message.created_at
    e.set_footer(text="TOSS Intro Bot made by Joyte", icon_url=bot.joy_url)

    log_channel = message.guild.get_channel(history.get_log_channel())

    await log_channel.send(embed=e)
    if len(message_links_formatted) > 5000:
        await log_channel.send(file=File("./" + str(message.author.id) + ".txt"))
        os.remove("./" + str(message.author.id) + ".txt")


@bot.event
async def on_raw_message_delete(payload: RawMessageDeleteEvent):
    history = History(payload.guild_id)
    if payload.channel_id != history.get_intro_channel():
        return

    if payload.cached_message:
        message = payload.cached_message
        if message.author.bot:
            return

        history.remove(message.author.id, message.id)

        role = utils.get(message.guild.roles, name="Staff")
        if role in message.author.roles:
            return

        e = Embed(colour=0xFF0000)
        e.title = f"Message Deleted"
        e.description = f"`{message.author}` **|** `{message.author.id}`\nA message was deleted, and it was removed from the database."
        e.add_field(name="Content", value=message.content, inline=False)
        if message.attachments:
            urls = "\n".join([attachment.url for attachment in message.attachments])
            e.add_field(name="Attachments", value=urls, inline=False)
        e.add_field(name="Link", value=f"[Link to message (won't work)](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})")
        e.set_thumbnail(url=message.author.avatar_url)
        e.timestamp = message.created_at
        e.set_footer(text="TOSS Intro Bot made by Joyte", icon_url=bot.joy_url)

        log_channel = message.guild.get_channel(history.get_log_channel())
        await log_channel.send(embed=e)

    else:
        guild = bot.get_guild(payload.guild_id)

        user_id = history.get_from_message_id(payload.message_id)
        if user_id == 0:
            return

        user = await bot.fetch_user(user_id)
        history.remove(user_id, payload.message_id)

        e = Embed(colour=0xFF0000)
        e.title = f"Message Deleted"
        e.description = f"`{user}` **|** `{user.id}` **|** Not cached\nA message was deleted, and it was removed from the database."
        e.add_field(name="Link", value=f"[Link to message (won't work)](https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id})")
        e.set_thumbnail(url=user.avatar_url)
        e.set_footer(text="TOSS Intro Bot made by Joyte", icon_url=bot.joy_url)

        log_channel = guild.get_channel(history.get_log_channel())
        await log_channel.send(embed=e)


@bot.event
async def on_raw_bulk_message_delete(payload: RawBulkMessageDeleteEvent):
    cached_msg_ids = set([message.id for message in payload.cached_messages])
    non_cached_msg_ids = payload.message_ids - cached_msg_ids

    history = History(payload.guild_id)
    if payload.channel_id != history.get_intro_channel():
        return

    for message_id in non_cached_msg_ids:
        guild = bot.get_guild(payload.guild_id)

        user_id = history.get_from_message_id(message_id)
        if user_id == 0:
            return

        user = await bot.fetch_user(user_id)
        history.remove(user_id, message_id)

        e = Embed(colour=0xFF0000)
        e.title = f"Message Deleted"
        e.description = f"`{user}` **|** `{user.id}` **|** Not cached\nA message was deleted, and it was removed from the database."
        e.add_field(name="Link", value=f"[Link to message (won't work)](https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{message_id})")
        e.set_thumbnail(url=user.avatar_url)
        e.set_footer(text="TOSS Intro Bot made by Joyte", icon_url=bot.joy_url)

        log_channel = guild.get_channel(history.get_log_channel())
        await log_channel.send(embed=e)

    for message in payload.cached_messages:
        if message.author.bot:
            return

        history.remove(message.author.id, message.id)

        role = utils.get(message.guild.roles, name="Staff")
        if role in message.author.roles:
            return

        e = Embed(colour=0xFF0000)
        e.title = f"Message Deleted"
        e.description = f"`{message.author}` **|** `{message.author.id}`\nA message was deleted, and it was removed from the database."
        e.add_field(name="Content", value=message.content, inline=False)
        if message.attachments:
            urls = "\n".join([attachment.url for attachment in message.attachments])
            e.add_field(name="Attachments", value=urls, inline=False)
        e.add_field(name="Link", value=f"[Link to message (won't work)](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})")
        e.set_thumbnail(url=message.author.avatar_url)
        e.timestamp = message.created_at
        e.set_footer(text="TOSS Intro Bot made by Joyte", icon_url=bot.joy_url)

        log_channel = message.guild.get_channel(history.get_log_channel())
        await log_channel.send(embed=e)


@bot.command()
async def fetchall(ctx: commands.Context, limit: int = 2000):
    """ Fetches all the intro posts """
    if ctx.author.id not in [246862123328733186]:
        await ctx.send("Hey, you can't use this!")
        return

    history = History(ctx.guild.id)
    intro_channel = history.get_intro_channel()

    if intro_channel == 0:
        await ctx.send("The intro channel hasn't been set!")
        return

    channel = ctx.guild.get_channel(intro_channel)

    msg = await ctx.send("Getting history... (this might take a while)")
    entire_history = await channel.history(limit=limit, oldest_first=True).flatten()

    await msg.edit(content="History gotten, beginning processing...")
    for entry in entire_history:
        history.add(entry.author.id, entry.id, commit=False)

    history.manual_commit()
    await msg.edit(content="Processing done! Enjoy your new database!")


@bot.command()
async def delete(ctx: commands.Context, message_id: int = None):
    """ Removes one from users post count """
    if ctx.author.id not in [246862123328733186]:
        await ctx.send("Hey, you can't use this!")
        return

    if message_id is None:
        await ctx.send("Please give a message ID to delete!")

    history = History(ctx.guild.id)

    channel = ctx.guild.get_channel(history.get_intro_channel())
    try:
        message = await channel.fetch_message(message_id)
        history.remove(message.author.id, message.id)

        await message.delete()
        await ctx.send("Removed the message from the database, and deleted the message!")

    except NotFound:
        user_id = history.get_from_message_id(message_id)
        if user_id == 0:
            await ctx.send("That's not a valid message id!")
            return

        history.remove(user_id, message_id)

        await ctx.send("Removed the message from the database, but the message was already deleted!")


@bot.command()
async def introset(ctx: commands.Context, channel: TextChannel = None):
    """ Sets the intro channel """
    if ctx.author.id not in [246862123328733186]:
        await ctx.send("Hey, you can't use this!")
        return

    if channel is None:
        await ctx.send("Please give a channel!")

    history = History(ctx.guild.id)
    history.set_channel_intro(channel.id)

    await ctx.send(f"Set the introduction channel to <#{channel.id}>")


@bot.command()
async def logset(ctx: commands.Context, channel: TextChannel = None):
    """ Sets the log channel """
    if ctx.author.id not in [246862123328733186]:
        await ctx.send("Hey, you can't use this!")
        return

    if channel is None:
        await ctx.send("Please give a channel ID!")

    history = History(ctx.guild.id)
    history.set_channel_log(channel.id)

    await ctx.send(f"Set the log channel to <#{channel.id}>")


@bot.command()
async def info(ctx: commands.Context, user: Union[Member, int] = None):
    """ Gets a user's intro information """
    not_in_guild = False
    if user is None:
        user = ctx.author

    elif type(user) is int:
        try:
            user = await bot.fetch_user(user)
        except NotFound:
            await ctx.send("That's not a valid user!")
            return

        not_in_guild = True

    history = History(ctx.guild.id)
    e = Embed(color=0xffff00)
    e.title = f"`{user}`'s intro information"
    e.description = None
    e.set_thumbnail(url=user.avatar_url)

    if history.get(user.id) == 0:
        e.add_field(name="Intro information", value="This person hasn't posted an introduction!", inline=False)
        message_links_formatted = ""

    else:
        e.add_field(name="Intro information", value=f"Times posted in intro: `{history.get(user.id)}`", inline=False)

        message_links_formatted = ""
        # noinspection PyTypeChecker
        for index, message_id in enumerate(history.get(user.id, ids=True)):
            message_links_formatted += f"[{index + 1}: {message_id}](https://discord.com/channels/{ctx.guild.id}/{history.get_intro_channel()}/{message_id})\n"

        if len(message_links_formatted) > 5000:
            with open(f"./{user.id}.txt", "w+") as fp:
                fp.write(message_links_formatted)

            message_links_formatted = "Check attached file"

        e.add_field(name="Links", value=message_links_formatted, inline=False)

    if not_in_guild and history.get(user.id) != 0:
        e.add_field(name="Guild", value="This user isn't in the guild, consider deleting all their posts!")

    await ctx.send(embed=e)
    if len(message_links_formatted) > 5000:
        await ctx.send(file=File("./" + str(user.id) + ".txt"))
        os.remove("./" + str(user.id) + ".txt")


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOSS_TOKEN"])
