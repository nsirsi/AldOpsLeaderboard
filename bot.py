import discord
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, date, timezone, timedelta
import datetime as dt
from typing import Optional, List, Dict
import pytz

from config import *
from database import WordleDatabase
from message_parser import WordleMessageParser

# Custom View class for interactive leaderboard buttons
class LeaderboardView(discord.ui.View):
    def __init__(self, bot_instance, initial_period="weekly"):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot_instance
        self.current_period = initial_period
        
        # Update button states based on current period
        self.update_button_states()
    
    def update_button_states(self):
        """Update button styles based on current period"""
        # Reset all buttons to secondary style
        self.weekly_button.style = discord.ButtonStyle.secondary
        self.monthly_button.style = discord.ButtonStyle.secondary
        self.alltime_button.style = discord.ButtonStyle.secondary
        
        # Highlight current period
        if self.current_period == "weekly":
            self.weekly_button.style = discord.ButtonStyle.primary
        elif self.current_period == "monthly":
            self.monthly_button.style = discord.ButtonStyle.primary
        elif self.current_period == "alltime":
            self.alltime_button.style = discord.ButtonStyle.primary
    
    async def update_leaderboard_embed(self, interaction: discord.Interaction):
        """Update the leaderboard embed with current period data"""
        try:
            # Get leaderboard data
            leaderboard_data = self.bot.db.get_leaderboard(self.current_period, limit=10)
            
            if not leaderboard_data:
                embed = discord.Embed(
                    title=f"🏆 {self.current_period.title()} Wordle Leaderboard",
                    description="No data available for this period.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title=f"🏆 {self.current_period.title()} Wordle Leaderboard",
                    description=f"**Top performers ({self.current_period}):**",
                    color=0x00ff00
                )
                
                # Add leaderboard entries
                for i, entry in enumerate(leaderboard_data, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    streak_display = f"🔥 {entry.get('current_streak', 0)}" if entry.get('current_streak', 0) > 0 else ""
                    embed.add_field(
                        name=f"{medal} {entry['display_name'] or entry['username']} {streak_display}",
                        value=f"Score: {entry['total_score']} | Games: {entry['games_played']} | Avg: {entry['average_score']}",
                        inline=False
                    )
            
            embed.set_footer(text="Click buttons to switch periods • Score = 8 - guesses; X = 1; no attempt = 0 • 🔥 = current streak")
            
            # Update the message
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error updating leaderboard embed: {e}")
            await interaction.response.send_message("Error updating leaderboard.", ephemeral=True)
    
    @discord.ui.button(label="Weekly", style=discord.ButtonStyle.secondary, emoji="📅")
    async def weekly_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_period = "weekly"
        self.update_button_states()
        await self.update_leaderboard_embed(interaction)
    
    @discord.ui.button(label="Monthly", style=discord.ButtonStyle.secondary, emoji="📆")
    async def monthly_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_period = "monthly"
        self.update_button_states()
        await self.update_leaderboard_embed(interaction)
    
    @discord.ui.button(label="All Time", style=discord.ButtonStyle.secondary, emoji="🏆")
    async def alltime_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_period = "alltime"
        self.update_button_states()
        await self.update_leaderboard_embed(interaction)
    
    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.success, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_leaderboard_embed(interaction)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WordleLeaderboardBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            help_command=None
        )
        
        self.db = WordleDatabase(DATABASE_PATH)
        self.parser = WordleMessageParser()
        self.auto_post_enabled = AUTO_POST_ENABLED
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")
        
        # Start auto-post task if enabled
        if self.auto_post_enabled:
            self.weekly_leaderboard_task.start()
            logger.info("Started weekly leaderboard auto-post task")
    
    async def on_message(self, message):
        """Handle incoming messages"""
        # Don't process bot messages
        if message.author.bot:
            return
        
        # Process WordleBot messages
        if self.parser.is_wordlebot_message(message):
            await self.process_wordlebot_message(message)
        
        # Process regular commands
        await self.process_commands(message)
    
    async def process_wordlebot_message(self, message):
        """Process a WordleBot message and update database"""
        try:
            # Parse the message
            parsed_data = self.parser.parse_wordlebot_message(message)
            if not parsed_data:
                logger.warning(f"Could not parse WordleBot message: {message.id}")
                return
            
            # Validate parsed data
            if not self.parser.validate_parsed_data(parsed_data):
                logger.error(f"Invalid parsed data for message: {message.id}")
                return
            
            # Process each player result
            processed_count = 0
            for result in parsed_data['player_results']:
                user_id = result['user_id']
                guesses = result['guesses']
                success = result['success']
                logger.info(
                    "process:result wordle_no=%s game_date=%s user_id=%s guesses=%s success=%s",
                    parsed_data['wordle_number'], parsed_data['game_date'], user_id, guesses, success
                )
                
                # Get user info
                user = self.parser.get_user_from_mention(message, user_id)
                if user:
                    # Add/update user in database
                    self.db.add_or_update_user(
                        user_id=user_id,
                        username=user.name,
                        display_name=user.display_name
                    )
                    
                    # Add game result
                    inserted = self.db.add_game_result(
                        user_id=user_id,
                        wordle_number=parsed_data['wordle_number'],
                        game_date=parsed_data['game_date'],
                        guesses=guesses,
                        success=success
                    )
                    if inserted:
                        processed_count += 1
                        logger.info(f"✓ Added game result for user {user.name} (id={user_id}): {guesses}/6 on {parsed_data['game_date']} (Wordle {parsed_data['wordle_number']})")
                    else:
                        logger.warning(f"✗ Game result already exists or failed for user {user.name} (id={user_id}): {guesses}/6 on {parsed_data['game_date']} (Wordle {parsed_data['wordle_number']})")
                else:
                    logger.warning(f"✗ Could not find user with ID: {user_id} in guild {message.guild.name if message.guild else 'None'}")
            
            if processed_count > 0:
                logger.info(f"Processed {processed_count} game results from WordleBot message")
            else:
                logger.warning("No game results were processed")
                
        except Exception as e:
            logger.error(f"Error processing WordleBot message: {e}")
    
    @tasks.loop(time=dt.time(hour=AUTO_POST_HOUR, minute=AUTO_POST_MINUTE))
    async def weekly_leaderboard_task(self):
        """Auto-post weekly leaderboard every Monday at 12:01 AM PT"""
        if not self.auto_post_enabled:
            return
        
        try:
            # Get current time in PT
            pt_tz = pytz.timezone('US/Pacific')
            now_pt = dt.datetime.now(pt_tz)
            
            # Check if it's Monday
            if now_pt.weekday() != AUTO_POST_DAY:
                return
            
            logger.info("Posting weekly leaderboard auto-update")
            
            # Post to all guilds
            for guild in self.guilds:
                try:
                    # Find a suitable channel (preferably general or wordle-related)
                    channel = None
                    
                    # Look for channels with 'general', 'wordle', or 'games' in the name
                    for ch in guild.text_channels:
                        if any(keyword in ch.name.lower() for keyword in ['general', 'wordle', 'games', 'bot']):
                            if ch.permissions_for(guild.me).send_messages:
                                channel = ch
                                break
                    
                    # Fallback to first available channel
                    if not channel:
                        for ch in guild.text_channels:
                            if ch.permissions_for(guild.me).send_messages:
                                channel = ch
                                break
                    
                    if channel:
                        await self.post_weekly_leaderboard(channel)
                    else:
                        logger.warning(f"No suitable channel found in guild {guild.name}")
                        
                except Exception as e:
                    logger.error(f"Error posting to guild {guild.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in weekly leaderboard task: {e}")
    
    async def post_weekly_leaderboard(self, channel):
        """Post weekly leaderboard to a specific channel"""
        try:
            # Create interactive view for auto-post
            view = LeaderboardView(self, "weekly")
            
            # Get weekly leaderboard data
            leaderboard_data = self.db.get_leaderboard('weekly', limit=10)
            
            if not leaderboard_data:
                embed = discord.Embed(
                    title="📊 Weekly Wordle Leaderboard",
                    description="No games played this week yet!",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="📊 Weekly Wordle Leaderboard",
                    description="🏆 **Top performers this week:**",
                    color=0x00ff00
                )
                
                # Add leaderboard entries
                for i, entry in enumerate(leaderboard_data, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    streak_display = f"🔥 {entry.get('current_streak', 0)}" if entry.get('current_streak', 0) > 0 else ""
                    embed.add_field(
                        name=f"{medal} {entry['display_name'] or entry['username']} {streak_display}",
                        value=f"Score: {entry['total_score']} | Games: {entry['games_played']} | Avg: {entry['average_score']}",
                        inline=False
                    )
            
            embed.set_footer(text="Auto-posted every Monday at 12:01 AM PT • Score = 8 - guesses; X = 1; no attempt = 0 • 🔥 = current streak")
            await channel.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error posting weekly leaderboard: {e}")
    
    async def setup_hook(self):
        """Set up slash commands"""
        # Leaderboard commands
        @self.tree.command(name="leaderboard", description="View interactive Wordle leaderboards")
        async def leaderboard(interaction: discord.Interaction, period: str = "weekly"):
            """Show interactive leaderboard with toggleable periods"""
            if period not in ["weekly", "monthly", "alltime"]:
                await interaction.response.send_message(
                    "Invalid period! Use: `weekly`, `monthly`, or `alltime`", 
                    ephemeral=True
                )
                return
            
            try:
                # Create interactive view
                view = LeaderboardView(self, period)
                
                # Get initial leaderboard data
                leaderboard_data = self.db.get_leaderboard(period, limit=10)
                
                if not leaderboard_data:
                    embed = discord.Embed(
                        title=f"🏆 {period.title()} Wordle Leaderboard",
                        description="No data available for this period.",
                        color=0x00ff00
                    )
                else:
                    embed = discord.Embed(
                        title=f"🏆 {period.title()} Wordle Leaderboard",
                        description=f"**Top performers ({period}):**",
                        color=0x00ff00
                    )
                    
                    # Add leaderboard entries
                    for i, entry in enumerate(leaderboard_data, 1):
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                        streak_display = f"🔥 {entry.get('current_streak', 0)}" if entry.get('current_streak', 0) > 0 else ""
                        embed.add_field(
                            name=f"{medal} {entry['display_name'] or entry['username']} {streak_display}",
                            value=f"Score: {entry['total_score']} | Games: {entry['games_played']} | Avg: {entry['average_score']}",
                            inline=False
                        )
                
                embed.set_footer(text="Click buttons to switch periods • Score = 8 - guesses; X = 1; no attempt = 0 • 🔥 = current streak")
                await interaction.response.send_message(embed=embed, view=view)
                
            except Exception as e:
                logger.error(f"Error getting leaderboard: {e}")
                await interaction.response.send_message(
                    "Error retrieving leaderboard data.", 
                    ephemeral=True
                )
        
        @self.tree.command(name="mystats", description="View your Wordle statistics")
        async def mystats(interaction: discord.Interaction, period: str = "alltime"):
            """Show user's personal statistics"""
            if period not in ["weekly", "monthly", "alltime"]:
                await interaction.response.send_message(
                    "Invalid period! Use: `weekly`, `monthly`, or `alltime`", 
                    ephemeral=True
                )
                return
            
            try:
                user_id = interaction.user.id
                stats = self.db.get_user_stats(user_id, period)
                rank = self.db.get_user_rank(user_id, period)
                streak = self.db.get_user_streak(user_id)
                
                if stats['games_played'] == 0:
                    await interaction.response.send_message(
                        f"No games found for {period} period.", 
                        ephemeral=True
                    )
                    return
                
                # Create embed
                embed = discord.Embed(
                    title=f"📊 Your {period.title()} Statistics",
                    color=0x0099ff
                )
                
                embed.add_field(name="Games Played", value=stats['games_played'], inline=True)
                embed.add_field(name="Total Score", value=stats['total_score'], inline=True)
                embed.add_field(name="Average Score", value=stats['average_score'], inline=True)
                embed.add_field(name="Success Rate", value=f"{stats['successful_games']}/{stats['games_played']}", inline=True)
                
                # Add streak information
                streak_text = f"🔥 {streak['current_streak']}"
                if streak['longest_streak'] > streak['current_streak']:
                    streak_text += f" (Best: {streak['longest_streak']})"
                embed.add_field(name="Streak", value=streak_text, inline=True)
                
                if rank > 0:
                    embed.add_field(name="Rank", value=f"#{rank}", inline=True)
                
                if stats['first_game'] and stats['last_game']:
                    embed.add_field(name="First Game", value=stats['first_game'], inline=True)
                    embed.add_field(name="Last Game", value=stats['last_game'], inline=True)
                
                embed.set_footer(text=f"Period: {period.title()}")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error getting user stats: {e}")
                await interaction.response.send_message(
                    "Error retrieving your statistics.", 
                    ephemeral=True
                )
        
        @self.tree.command(name="toggle", description="Toggle leaderboard display on/off")
        async def toggle_leaderboard(interaction: discord.Interaction):
            """Toggle leaderboard display"""
            try:
                # This is a simple toggle - in a real implementation, you'd store this in the database
                # For now, we'll just show the current status
                status = "enabled" if self.auto_post_enabled else "disabled"
                
                embed = discord.Embed(
                    title="🔧 Leaderboard Toggle",
                    description=f"Auto-post is currently **{status}**",
                    color=0x0099ff
                )
                
                embed.add_field(
                    name="Current Settings",
                    value=f"• Auto-post: {status}\n• Schedule: Every Monday at 12:01 AM PT\n• Channels: Auto-detected",
                    inline=False
                )
                
                embed.add_field(
                    name="Manual Commands",
                    value="• `/leaderboard` - View any period\n• `/mystats` - Your personal stats",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error in toggle command: {e}")
                await interaction.response.send_message(
                    "Error toggling leaderboard settings.", 
                    ephemeral=True
                )
        
        @self.tree.command(name="post", description="Manually post interactive leaderboard")
        async def manual_post(interaction: discord.Interaction):
            """Manually trigger interactive leaderboard post"""
            try:
                await interaction.response.defer(ephemeral=True)
                
                # Create interactive view
                view = LeaderboardView(self, "weekly")
                
                # Get weekly leaderboard data
                leaderboard_data = self.db.get_leaderboard('weekly', limit=10)
                
                if not leaderboard_data:
                    embed = discord.Embed(
                        title="📊 Weekly Wordle Leaderboard",
                        description="No games played this week yet!",
                        color=0x00ff00
                    )
                else:
                    embed = discord.Embed(
                        title="📊 Weekly Wordle Leaderboard",
                        description="🏆 **Top performers this week:**",
                        color=0x00ff00
                    )
                    
                    # Add leaderboard entries
                    for i, entry in enumerate(leaderboard_data, 1):
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                        streak_display = f"🔥 {entry.get('current_streak', 0)}" if entry.get('current_streak', 0) > 0 else ""
                        embed.add_field(
                            name=f"{medal} {entry['display_name'] or entry['username']} {streak_display}",
                            value=f"Score: {entry['total_score']} | Games: {entry['games_played']} | Avg: {entry['average_score']}",
                            inline=False
                        )
                
                embed.set_footer(text="Click buttons to switch periods • Score = 8 - guesses; X = 1; no attempt = 0 • 🔥 = current streak")
                await interaction.channel.send(embed=embed, view=view)
                await interaction.followup.send("✅ Interactive leaderboard posted!", ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error in manual post: {e}")
                await interaction.followup.send(
                    "Error posting leaderboard.", 
                    ephemeral=True
                )
        
        @self.tree.command(name="help", description="Show available commands")
        async def help_command(interaction: discord.Interaction):
            """Show help information"""
            embed = discord.Embed(
                title="🤖 Wordle Leaderboard Bot Help",
                description="Commands to track and display Wordle leaderboards",
                color=0x00ff00
            )
            
            embed.add_field(
                name="/leaderboard [period]",
                value="View interactive leaderboards with toggleable buttons\nPeriods: `weekly`, `monthly`, `alltime`",
                inline=False
            )
            
            embed.add_field(
                name="/mystats [period]",
                value="View your personal statistics\nPeriods: `weekly`, `monthly`, `alltime`",
                inline=False
            )
            
            embed.add_field(
                name="/toggle",
                value="Toggle auto-post settings and view status",
                inline=False
            )
            
            embed.add_field(
                name="/post",
                value="Manually post interactive leaderboard to current channel",
                inline=False
            )
            
            embed.add_field(
                name="Interactive Features",
                value="• Click buttons to switch between weekly/monthly/all-time\n• Refresh button to update data\n• 5-minute timeout for interactions",
                inline=False
            )
            
            embed.add_field(
                name="Automatic Features",
                value="• Processes WordleBot messages automatically\n• Posts interactive leaderboard every Monday at 12:01 AM PT",
                inline=False
            )
            
            embed.set_footer(text="Score = 8 - guesses; X = 1; no attempt = 0")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.tree.command(name="backfill", description="Admin: backfill recent WordleBot history")
        async def backfill(
            interaction: discord.Interaction,
            days: int = 7,
            channel: Optional[discord.TextChannel] = None
        ):
            """Backfill recent history by scanning for WordleBot messages."""
            # Restrict to users with Manage Guild permission
            if not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message("You need Manage Server permission to run backfill.", ephemeral=True)
                return

            target_channel = channel or interaction.channel
            await interaction.response.defer(ephemeral=True, thinking=True)

            try:
                after_dt = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 60)))
                processed_messages = 0
                processed_results = 0

                async for msg in target_channel.history(limit=None, after=after_dt):
                    if self.parser.is_wordlebot_message(msg):
                        parsed = self.parser.parse_wordlebot_message(msg)
                        if not parsed:
                            continue
                        for result in parsed['player_results']:
                            user_id = result['user_id']
                            guesses = result['guesses']
                            success = result['success']

                            user = self.parser.get_user_from_mention(msg, user_id)
                            if user:
                                self.db.add_or_update_user(
                                    user_id=user_id,
                                    username=user.name,
                                    display_name=getattr(user, 'display_name', None)
                                )
                                if self.db.add_game_result(
                                    user_id=user_id,
                                    wordle_number=parsed['wordle_number'],
                                    game_date=parsed['game_date'],
                                    guesses=guesses,
                                    success=success
                                ):
                                    processed_results += 1
                        processed_messages += 1

                await interaction.followup.send(
                    f"✅ Backfill complete in #{target_channel.name}: processed {processed_messages} messages, added {processed_results} results.",
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error during backfill: {e}")
                await interaction.followup.send("Error during backfill.", ephemeral=True)

# Create bot instance
bot = WordleLeaderboardBot()

# Run the bot
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables!")
        exit(1)
    
    bot.run(DISCORD_TOKEN)
