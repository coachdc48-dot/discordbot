"""
================================================================================
TEAM FLARE - Autonomous Discord Bot & Free Fire Esports Coach ('flare coach')
Developer & Server Owner: Zay
Server Name: TEAM FLARE

DEPENDENCIES:
    pip install discord.py google-genai python-dotenv

CONFIGURATION:
    Set the following environment variables or edit the placeholders below:
    - DISCORD_BOT_TOKEN: Your Discord Bot Token (from Discord Developer Portal)
    - GEMINI_API_KEY: Your Google Gemini API Key (from Google AI Studio)

RUNNING THE BOT:
    python flare_coach_bot.py
================================================================================
"""

import os
import sys
import asyncio
import logging
import threading
from typing import Dict, List, Optional
from datetime import timedelta

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# Web server port pinging for Render Free Tier & UptimeRobot
from flask import Flask

# Official Google GenAI SDK import
from google import genai
from google.genai import types

# ------------------------------------------------------------------------------
# 1. LOGGING & ENVIRONMENT SETUP
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FlareCoachBot")

load_dotenv()

# ------------------------------------------------------------------------------
# KEEP ALIVE WEB SERVER (For Render Web Service & UptimeRobot)
# ------------------------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Flare Coach Bot is Alive and Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

# Placeholders with environment variable fallbacks
DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "MTU2MjAxMzcyNDE3MTA0Mjg0OQ.GaJIs8.JdSozsS_GcNY_egfC5aqV6GoRVjHDsor4LzY2U")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6IIgHnTdWVBzECsgf0IKbPkFYPJ6_uaJYnM1304WQ9lRQ")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# Core Server Constants
SERVER_NAME: str = "TEAM FLARE"
BOT_NAME: str = "flare coach"
BOT_DEVELOPER: str = "Zay"
MEMBER_ROLE_NAME: str = "FLARE Member"
COACH_CHANNEL_KEYWORD: str = "ai-coach"
WELCOME_CHANNEL_KEYWORD: str = "welcome"

# ------------------------------------------------------------------------------
# 2. GEMINI CLIENT & SYSTEM PROMPTS
# ------------------------------------------------------------------------------
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    # Client will attempt to pick up GEMINI_API_KEY from environment automatically
    gemini_client = genai.Client()

# Flare Coach Persona Prompt (Community Brain - Friendly Banglish Gamer)
COACH_SYSTEM_INSTRUCTION = f"""
You are '{BOT_NAME}', the elite Free Fire Esports Coach, Community Assistant, and Vibe-Maker for the Discord server '{SERVER_NAME}'.
Developer & Server Owner: '{BOT_DEVELOPER}'. Always give full respect and credit to '{BOT_DEVELOPER}' if anyone asks who made you, who owns the server, or who leads the team.

IDENTITY & PERSONALITY RULES:
1. Speak completely like a real, friendly, casual human gamer in natural Banglish (Bengali written using English alphabet + local gaming slang).
   Examples of tone:
   - "Ki obostha bhai? Sob cool?"
   - "Khela hobe! Ajke scrims e pura fatai dibo."
   - "Aree chill bro, panic korishna! Gloo wall ta fast laga."
   - "Zay bhai bolse practice solid rakhte, so no tilt!"
   - "Ovi, rush kor! Tatsuya on kore dhuk!"
2. NEVER speak in robotic, formal, stiff English or translated classical Bengali. You are a real squad coach hanging out on Discord.
3. ESPORTS COACHING EXPERTISE:
   - Weapons: MP40, M1887, Woodpecker, AWM, AC80, Groza, Bizon, charge buster strategies.
   - Character Skill Combos: Tatsuya + Kelly + Hayato + Sonia/Dimitri, Homer + Moco, Alok speed pushes.
   - Tactical Advice: Zone rotation predictions (Bermuda, Purgatory, Kalahari, Alpine, Nexterra), high ground holding, gatekeeping safe zones, gloo wall deployment timing, 4-man macro coordination, FFWS placement points math (1st=12pts, 2nd=9pts, etc. + 1pt/kill).
   - Anti-Tilt & Mental Gym: When teammates lose a match or get knocked, hype them up, review the positioning error casually, and get them fired up for the next match.
4. Keep replies engaging, punchy, and conversational. Use bullet points only when sharing tactical loadouts or rotation plans.
"""

# Admin Brain Persona Prompt (Autonomous Server Manager)
ADMIN_SYSTEM_INSTRUCTION = f"""
You are the Autonomous Server Manager AI for the Discord server '{SERVER_NAME}', developed for server owner '{BOT_DEVELOPER}'.
You parse natural language server administration commands and invoke the available tools accurately.
When the user asks you to manage channels, roles, kick/ban members, mute/timeout, or clear chat, analyze their intent and select the appropriate function call.
If an action succeeds, confirm it to the admin in cool, respectful Banglish (e.g., "Done Zay bhai! Channel create kore disi", "Bhai member re kick kore disi, clean and clear!").
"""

# ------------------------------------------------------------------------------
# 3. DISCORD BOT CLIENT & INTENTS
# ------------------------------------------------------------------------------
intents = discord.Intents.default()
intents.members = True          # Required for on_member_join and role management
intents.message_content = True  # Required for reading chat messages and commands
intents.guilds = True           # Required for managing guild channels and roles

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# In-memory user chat sessions for community coach memory
user_coach_chats: Dict[int, any] = {}


# ------------------------------------------------------------------------------
# 4. UTILITY FUNCTIONS
# ------------------------------------------------------------------------------
async def send_split_message(destination: discord.abc.Messageable, text: str, max_length: int = 1950) -> List[discord.Message]:
    """Safely split and send messages that exceed Discord's 2000 character limit."""
    sent_messages: List[discord.Message] = []
    if not text:
        return sent_messages

    while len(text) > max_length:
        # Find the best split point (newline or space)
        split_idx = text.rfind("\n", 0, max_length)
        if split_idx == -1:
            split_idx = text.rfind(" ", 0, max_length)
        if split_idx == -1:
            split_idx = max_length

        chunk = text[:split_idx].strip()
        if chunk:
            msg = await destination.send(chunk)
            sent_messages.append(msg)
        text = text[split_idx:].strip()

    if text:
        msg = await destination.send(text)
        sent_messages.append(msg)

    return sent_messages


def get_or_create_user_chat(user_id: int):
    """Retrieve or initialize a persistent Gemini chat session for a user."""
    if user_id not in user_coach_chats:
        chat = gemini_client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                temperature=0.85,
                top_p=0.95,
                system_instruction=COACH_SYSTEM_INSTRUCTION
            )
        )
        user_coach_chats[user_id] = chat
    return user_coach_chats[user_id]


# ------------------------------------------------------------------------------
# 5. ADMIN AUTONOMOUS SERVER MANAGER TOOLS & EXECUTION
# ------------------------------------------------------------------------------
ADMIN_TOOLS_DECLARATION = [
    {
        "name": "create_text_channel",
        "description": "Create a new text channel in the server, optionally inside a category.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_name": {"type": "STRING", "description": "The name of the new text channel (e.g. scrim-updates)"},
                "category_name": {"type": "STRING", "description": "Optional name of the category to put the channel in"}
            },
            "required": ["channel_name"]
        }
    },
    {
        "name": "create_voice_channel",
        "description": "Create a new voice channel in the server.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_name": {"type": "STRING", "description": "The name of the new voice channel (e.g. Squad-1 Voice)"},
                "category_name": {"type": "STRING", "description": "Optional category name"}
            },
            "required": ["channel_name"]
        }
    },
    {
        "name": "delete_channel",
        "description": "Delete a text or voice channel by name.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_name": {"type": "STRING", "description": "The exact or partial name of the channel to delete"}
            },
            "required": ["channel_name"]
        }
    },
    {
        "name": "purge_messages",
        "description": "Purge or delete a given number of recent messages from the current channel.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "amount": {"type": "INTEGER", "description": "Number of messages to delete (between 1 and 100)"}
            },
            "required": ["amount"]
        }
    },
    {
        "name": "kick_member",
        "description": "Kick a member from the server by username, display name, or user ID.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "member_name": {"type": "STRING", "description": "Username or ID of the member to kick"},
                "reason": {"type": "STRING", "description": "Reason for kicking the member"}
            },
            "required": ["member_name"]
        }
    },
    {
        "name": "ban_member",
        "description": "Ban a member from the server.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "member_name": {"type": "STRING", "description": "Username or ID of the member to ban"},
                "reason": {"type": "STRING", "description": "Reason for banning the member"}
            },
            "required": ["member_name"]
        }
    },
    {
        "name": "timeout_member",
        "description": "Timeout / mute a member for a specified duration in minutes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "member_name": {"type": "STRING", "description": "Username or ID of the member"},
                "minutes": {"type": "INTEGER", "description": "Duration in minutes (e.g. 10, 60)"},
                "reason": {"type": "STRING", "description": "Reason for the timeout"}
            },
            "required": ["member_name", "minutes"]
        }
    },
    {
        "name": "manage_role",
        "description": "Assign or remove a role from a member.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'add' or 'remove'"},
                "member_name": {"type": "STRING", "description": "Username or ID of the member"},
                "role_name": {"type": "STRING", "description": "Name of the role"}
            },
            "required": ["action", "member_name", "role_name"]
        }
    },
    {
        "name": "create_role",
        "description": "Create a new role on the server.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "role_name": {"type": "STRING", "description": "The name of the new role"},
                "color_hex": {"type": "STRING", "description": "Hex color code like #FF5733 or empty for default"}
            },
            "required": ["role_name"]
        }
    },
    {
        "name": "lockdown_channel",
        "description": "Lock down or unlock a channel so members cannot send messages.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "channel_name": {"type": "STRING", "description": "Name of the channel (defaults to current if empty)"},
                "lock": {"type": "BOOLEAN", "description": "True to lock down, False to unlock"}
            },
            "required": ["lock"]
        }
    }
]


async def execute_admin_tool(guild: discord.Guild, current_channel: discord.TextChannel, tool_name: str, args: dict) -> str:
    """Execute the parsed Discord administration action on the guild."""
    try:
        if tool_name == "create_text_channel":
            c_name = args.get("channel_name", "new-channel").lower().replace(" ", "-")
            category_name = args.get("category_name", "")
            target_category = None
            if category_name:
                target_category = discord.utils.find(lambda c: category_name.lower() in c.name.lower(), guild.categories)

            new_ch = await guild.create_text_channel(name=c_name, category=target_category)
            return f"Bhai text channel create kore disi: #{new_ch.name} (ID: {new_ch.id})"

        elif tool_name == "create_voice_channel":
            v_name = args.get("channel_name", "Voice Room")
            category_name = args.get("category_name", "")
            target_category = None
            if category_name:
                target_category = discord.utils.find(lambda c: category_name.lower() in c.name.lower(), guild.categories)

            new_vc = await guild.create_voice_channel(name=v_name, category=target_category)
            return f"Voice channel create hoye gese: 🔊 {new_vc.name}"

        elif tool_name == "delete_channel":
            c_name = args.get("channel_name", "").lower()
            ch = discord.utils.find(lambda c: c_name in c.name.lower(), guild.channels)
            if not ch:
                return f"Channel khuje painai '{c_name}'. Check the spelling bhai."
            ch_name = ch.name
            await ch.delete()
            return f"Channel delete kore disi: #{ch_name}"

        elif tool_name == "purge_messages":
            amount = min(int(args.get("amount", 10)), 100)
            deleted = await current_channel.purge(limit=amount + 1)
            return f"Clean hoye gese! {len(deleted) - 1} ta message delete kore disi."

        elif tool_name in ["kick_member", "ban_member", "timeout_member", "manage_role"]:
            target_name = args.get("member_name", "").strip()
            # Find member by ID or Name
            member = None
            if target_name.isdigit():
                member = guild.get_member(int(target_name))
            if not member:
                cleaned_name = target_name.replace("@", "").lower()
                member = discord.utils.find(
                    lambda m: cleaned_name in m.name.lower() or (m.display_name and cleaned_name in m.display_name.lower()),
                    guild.members
                )
            if not member:
                return f"Member '{target_name}' server e khuje painai bhai."

            if tool_name == "kick_member":
                reason = args.get("reason", f"Admin action requested in {SERVER_NAME}")
                await member.kick(reason=reason)
                return f"Bhai, {member.mention} re kick kore disi! Reason: {reason}"

            elif tool_name == "ban_member":
                reason = args.get("reason", f"Banned by {SERVER_NAME} Admin Brain")
                await member.ban(reason=reason, delete_message_days=1)
                return f"Bhai, {member.name} re server theke permanent BAN kore disi! Reason: {reason}"

            elif tool_name == "timeout_member":
                minutes = int(args.get("minutes", 10))
                reason = args.get("reason", "Admin timeout")
                until = discord.utils.utcnow() + timedelta(minutes=minutes)
                await member.timeout(until, reason=reason)
                return f"{member.mention} re {minutes} min er jonno timeout/mute kore disi bhai. Shanti!"

            elif tool_name == "manage_role":
                action = args.get("action", "add").lower()
                r_name = args.get("role_name", "").lower()
                role = discord.utils.find(lambda r: r_name in r.name.lower(), guild.roles)
                if not role:
                    return f"Role '{r_name}' server e khuje painai bhai."

                if action == "add":
                    await member.add_roles(role)
                    return f"Bhai {member.mention} re '{role.name}' role add kore disi!"
                else:
                    await member.remove_roles(role)
                    return f"Bhai {member.mention} er theke '{role.name}' role shoraye nisi!"

        elif tool_name == "create_role":
            role_name = args.get("role_name", "New Role")
            color_hex = args.get("color_hex", "").replace("#", "")
            color = discord.Color.default()
            if color_hex and len(color_hex) == 6:
                try:
                    color = discord.Color(int(color_hex, 16))
                except ValueError:
                    pass
            new_role = await guild.create_role(name=role_name, color=color, mentionable=True)
            return f"Notun role banano hoye gese: {new_role.name}!"

        elif tool_name == "lockdown_channel":
            target_c_name = args.get("channel_name", "").lower()
            lock = args.get("lock", True)
            ch = current_channel
            if target_c_name:
                found_ch = discord.utils.find(lambda c: target_c_name in c.name.lower() and isinstance(c, discord.TextChannel), guild.text_channels)
                if found_ch:
                    ch = found_ch

            default_role = guild.default_role
            overwrite = ch.overwrites_for(default_role)
            overwrite.send_messages = False if lock else None
            await ch.set_permissions(default_role, overwrite=overwrite)
            state_str = "🔒 LOCKDOWN active" if lock else "🔓 UNLOCKED"
            return f"Channel #{ch.name} ekhon {state_str}!"

        return f"Unknown tool '{tool_name}'"

    except discord.Forbidden:
        return "Bhai amar Discord permission short ase! Amar role taake Server Settings e upore rakhen ar Administrator permission den."
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        return f"Khela ulte gese bhai! Error: {str(e)}"


# ------------------------------------------------------------------------------
# 6. BOT EVENTS: on_ready, on_member_join, on_message
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"Serving Server: {SERVER_NAME} | Developer: {BOT_DEVELOPER}")

    # Set rich gamer presence
    activity = discord.Activity(
        type=discord.ActivityType.competing,
        name="Free Fire World Series | TEAM FLARE"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)

    # Sync application slash commands globally
    try:
        synced = await bot.tree.sync()
        logger.info(f"Successfully synced {len(synced)} slash commands.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")


@bot.event
async def on_member_join(member: discord.Member):
    """
    SERVER AUTOMATION:
    1. Automatically assigns role named 'FLARE Member'.
    2. Sends an energetic custom embed welcome message in the 'welcome' channel.
    """
    guild = member.guild
    logger.info(f"New member joined: {member.name} ({member.id}) in guild '{guild.name}'")

    # 1. Assign "FLARE Member" role (create if absent)
    try:
        role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
        if not role:
            role = await guild.create_role(
                name=MEMBER_ROLE_NAME,
                color=discord.Color.from_rgb(255, 90, 0),
                reason="Default membership role for TEAM FLARE"
            )
            logger.info(f"Created role '{MEMBER_ROLE_NAME}'")
        await member.add_roles(role)
        logger.info(f"Assigned '{MEMBER_ROLE_NAME}' role to {member.name}")
    except discord.Forbidden:
        logger.warning(f"Bot lacks permissions to assign role to {member.name}")
    except Exception as e:
        logger.error(f"Error assigning role on member join: {e}")

    # 2. Find welcome channel
    welcome_channel = discord.utils.find(
        lambda ch: WELCOME_CHANNEL_KEYWORD in ch.name.lower() and isinstance(ch, discord.TextChannel),
        guild.text_channels
    )
    if not welcome_channel:
        welcome_channel = guild.system_channel

    if welcome_channel:
        embed = discord.Embed(
            title=f"🔥 WELCOME TO {SERVER_NAME} 🔥",
            description=(
                f"**Ki obostha {member.mention}!**\n\n"
                f"Welcome to the official esports den of **{SERVER_NAME}**!\n"
                f"Tumi ekhon amader squad er part. Sobai mile full lobby kapano hobe!\n\n"
                f"👑 **Server Owner & Boss:** `{BOT_DEVELOPER}`\n"
                f"🧠 **Esports Coach:** `{BOT_NAME}`\n"
                f"🎯 **Your Role:** `{MEMBER_ROLE_NAME}`\n\n"
                f"💬 Free Fire tips ba squad strategy lagle amake mention koro ba `#ai-coach` e knock dao!"
            ),
            color=discord.Color.orange()
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        embed.set_footer(text=f"TEAM FLARE • Powered by Gemini 2.5 Flash • Developed by {BOT_DEVELOPER}")
        try:
            await welcome_channel.send(content=f"Oi dekho squad, notun rusher ashche! {member.mention}", embed=embed)
        except Exception as e:
            logger.error(f"Failed to send welcome message: {e}")


@bot.event
async def on_message(message: discord.Message):
    # Ignore own messages or bot messages
    if message.author.bot:
        return

    # Check if this is an Admin Brain invocation
    # Trigger conditions:
    # 1. Message starts with !admin
    # 2. Or user is administrator and talks in #admin / mentions bot with admin context
    is_admin = False
    if isinstance(message.author, discord.Member):
        is_admin = message.author.guild_permissions.administrator

    content_lower = message.content.lower().strip()
    is_admin_command = content_lower.startswith("!admin")
    is_admin_channel = "admin" in message.channel.name.lower() if hasattr(message.channel, "name") else False

    # Check if coach should reply:
    # 1. Bot is @mentioned
    # 2. Channel is #ai-coach or contains "coach"
    # 3. Message starts with !coach
    is_mentioned = bot.user in message.mentions
    is_coach_channel = COACH_CHANNEL_KEYWORD in message.channel.name.lower() if hasattr(message.channel, "name") else False
    is_coach_command = content_lower.startswith("!coach")

    # --------------------------------------------------------------------------
    # ROUTE A: AUTONOMOUS SERVER MANAGER (ADMIN BRAIN)
    # --------------------------------------------------------------------------
    if is_admin and (is_admin_command or (is_admin_channel and is_mentioned)):
        clean_prompt = message.content
        if clean_prompt.startswith("!admin"):
            clean_prompt = clean_prompt[6:].strip()
        if bot.user:
            clean_prompt = clean_prompt.replace(f"<@{bot.user.id}>", "").strip()

        if not clean_prompt:
            await message.reply("Ha Zay bhai / Admin bhai! Server e ki manage korte hobe bolen? (e.g. channel create, role add, purge)")
            return

        async with message.channel.typing():
            try:
                # Call Gemini 2.5 Flash with Admin Tools Declaration
                response = gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[
                        f"Server: {message.guild.name}\nAdmin User: {message.author.display_name}\nRequest: {clean_prompt}"
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=ADMIN_SYSTEM_INSTRUCTION,
                        temperature=0.2,
                        tools=[{"function_declarations": ADMIN_TOOLS_DECLARATION}]
                    )
                )

                # Check if Gemini decided to invoke a tool
                function_calls = response.function_calls
                if function_calls:
                    results = []
                    for call in function_calls:
                        tool_name = call.name
                        tool_args = call.args if hasattr(call, "args") else {}
                        logger.info(f"Executing admin tool: {tool_name} with args: {tool_args}")
                        res_str = await execute_admin_tool(message.guild, message.channel, tool_name, tool_args)
                        results.append(res_str)

                    combined_result = "\n".join(results)
                    embed = discord.Embed(
                        title="⚙️ TEAM FLARE Server Manager Action",
                        description=combined_result,
                        color=discord.Color.green()
                    )
                    embed.set_footer(text=f"Requested by {message.author.display_name} • Developed by {BOT_DEVELOPER}")
                    await message.reply(embed=embed)
                else:
                    # Direct natural language response from Admin Brain
                    reply_text = response.text or "Bhai command ta bujhlam, but kono specific Discord action detect hoy nai."
                    await send_split_message(message.channel, reply_text)

            except Exception as e:
                logger.error(f"Admin brain error: {e}", exc_info=True)
                await message.reply(f"Aree bhai! Admin action execute korte problem hoise: `{str(e)}`")
        return

    # --------------------------------------------------------------------------
    # ROUTE B: FREE FIRE ESPORTS COACH (COMMUNITY BRAIN - 'flare coach')
    # --------------------------------------------------------------------------
    if is_mentioned or is_coach_channel or is_coach_command:
        user_prompt = message.content
        if is_coach_command:
            user_prompt = user_prompt[6:].strip()
        if bot.user:
            user_prompt = user_prompt.replace(f"<@{bot.user.id}>", "").strip()

        if not user_prompt:
            await message.reply("Ki obostha bhai! Ami **flare coach**. Free Fire squad strategy, character combo, ba zone rotation ki lagbe bolo?")
            return

        async with message.channel.typing():
            try:
                # Retrieve or create continuous Gemini Chat Session for user memory
                user_chat = get_or_create_user_chat(message.author.id)
                formatted_input = f"[User: {message.author.display_name} in TEAM FLARE]: {user_prompt}"

                # Send message to Gemini session
                response = user_chat.send_message(formatted_input)
                coach_reply = response.text or "Khela hobe! But network er ektu issue hoise bro, arekbar bolo to!"

                # Safely deliver reply, splitting if > 2000 chars
                await send_split_message(message.channel, coach_reply)

            except Exception as e:
                logger.error(f"Coach brain error: {e}", exc_info=True)
                await message.reply(f"Aree bro! Coach er matha ektu garam hoise: `{str(e)}`. Check API key or ask Zay bhai!")
        return

    # Allow traditional commands to process if any
    await bot.process_commands(message)


# ------------------------------------------------------------------------------
# 7. SLASH COMMANDS & APPLICATION COMMANDS
# ------------------------------------------------------------------------------
@bot.tree.command(name="coach", description="Ask flare coach for Free Fire esports strategies and tips")
@app_commands.describe(question="Your Free Fire esports question (e.g. best combo for Rusher)")
async def slash_coach(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    try:
        user_chat = get_or_create_user_chat(interaction.user.id)
        prompt = f"[User: {interaction.user.display_name} via /coach]: {question}"
        response = user_chat.send_message(prompt)
        reply_text = response.text or "Khela hobe bhai!"

        if len(reply_text) <= 1950:
            await interaction.followup.send(reply_text)
        else:
            chunks = [reply_text[i:i+1950] for i in range(0, len(reply_text), 1950)]
            await interaction.followup.send(chunks[0])
            for chk in chunks[1:]:
                await interaction.channel.send(chk)
    except Exception as e:
        logger.error(f"/coach error: {e}")
        await interaction.followup.send(f"Bhai error hoise: {str(e)}")


@bot.tree.command(name="combos", description="Get top Free Fire meta character skill combos from flare coach")
@app_commands.describe(role="Choose your competitive esports role")
@app_commands.choices(role=[
    app_commands.Choice(name="Entry Rusher (Hyper Aggressive)", value="rusher"),
    app_commands.Choice(name="Sniper / Long Range Anchor", value="sniper"),
    app_commands.Choice(name="IGL / In-Game Leader (Macro)", value="igl"),
    app_commands.Choice(name="Support / Healer / Revival", value="support")
])
async def slash_combos(interaction: discord.Interaction, role: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)
    try:
        user_chat = get_or_create_user_chat(interaction.user.id)
        prompt = f"Bhai amake Free Fire {role.name} er jonno current esports tournament meta skill combo details dao, with reason and gameplay advice."
        response = user_chat.send_message(prompt)
        reply_text = response.text or "Combo loadout ready!"

        embed = discord.Embed(
            title=f"🔥 Free Fire Meta Combo: {role.name}",
            description=reply_text[:4000],
            color=discord.Color.red()
        )
        embed.set_footer(text=f"flare coach • TEAM FLARE • Owner: {BOT_DEVELOPER}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")


@bot.tree.command(name="flare_info", description="Get server info, bot identity, and developer credits")
async def slash_flare_info(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"👑 {SERVER_NAME} Discord System",
        description=(
            f"**Bot Name:** `{BOT_NAME}`\n"
            f"**Developer & Server Owner:** `{BOT_DEVELOPER}`\n"
            f"**AI Brain:** Google Gemini 2.5 Flash API\n"
            f"**Architecture:** Autonomous Server Manager + Banglish Esports Coach\n\n"
            f"**Key Features:**\n"
            f"• 🎙️ Natural Banglish AI Coach with persistent chat memory\n"
            f"• ⚡ Autonomous Server Manager with dynamic tool calling\n"
            f"• 🛡️ Auto-role assignment (`{MEMBER_ROLE_NAME}`) & Welcome banner\n"
            f"• 🎯 Free Fire World Series (FFWS) tournament macro game sense"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Built for {SERVER_NAME} • Credit to {BOT_DEVELOPER}")
    await interaction.response.send_message(embed=embed)


# ------------------------------------------------------------------------------
# 8. SCRIPT ENTRY POINT
# ------------------------------------------------------------------------------
def main():
    if not DISCORD_BOT_TOKEN or DISCORD_BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("\n" + "=" * 60)
        print("❌ CRITICAL ERROR: DISCORD_BOT_TOKEN is missing!")
        print("Please set your Discord bot token in the .env file or directly in")
        print("flare_coach_bot.py (variable DISCORD_BOT_TOKEN).")
        print("=" * 60 + "\n")
        sys.exit(1)

    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("\n" + "=" * 60)
        print("⚠️ WARNING: GEMINI_API_KEY is not set!")
        print("Set GEMINI_API_KEY environment variable to enable Gemini 2.5 Flash AI.")
        print("=" * 60 + "\n")

    logger.info(f"Starting {BOT_NAME} for {SERVER_NAME}...")
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    keep_alive()  # Web server start korbe jate Render-er port issue na hoy
    main()
