import disnake
import calendar
import coc

from disnake.ext import commands
from typing import List
from classes.player.stats import StatsPlayer
from classes.bot import CustomClient
from exceptions.CustomExceptions import *
from operator import attrgetter
from datetime import date, timedelta, datetime

from utility.discord_utils import interaction_handler
from utility.player_pagination import button_pagination
from utility.components import player_components
from utility.search import search_results
from discord.options import convert, autocomplete
from .utils import detailed_player_board, to_do_embed, player_accounts
#from CommandsOlder.Utils.Player import create_profile_troops


class PlayerCommands(commands.Cog, name="Player Commands"):
    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="player")
    async def player(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()


    @player.sub_command(name="lookup", description="Lookup a player or discord user")
    async def lookup(self, ctx: disnake.ApplicationCommandInteraction,
                     player: StatsPlayer = commands.Param(default=None,
                                                         converter=convert.custom_player,
                                                         autocomplete=autocomplete.family_players),
                     discord_user: disnake.Member = None):
        """
            Parameters
            ----------
            player: (optional) player to lookup
            discord_user: (optional) discord user to lookup
        """
        '''players = [player]
        if discord_user:
            user_accounts = await self.bot.link_client.get_linked_players(discord_id=discord_user.id)
            players = await self.bot.get_players(tags=user_accounts, custom=True)
            if not players:
                raise MessageException(f"{discord_user.name} has no accounts linked.")
            players.sort(key=lambda l: l.trophies, reverse=True)
            player = players[0]

        options = [  # the options in your dropdown
            disnake.SelectOption(label="Overview", value=f"playerdetailed:{player.tag}"),
            # disnake.SelectOption(label="Troops", emoji=bot.emoji.troop.partial_emoji, value="Troops"),
            # disnake.SelectOption(label="Upgrades/Rushed", emoji=bot.emoji.clock.partial_emoji, value="Upgrades"),
            # disnake.SelectOption(label="Clan History", emoji=bot.emoji.clan_castle.partial_emoji, value="History"),
        ]
        row_one = disnake.ui.ActionRow(disnake.ui.Select(options=options, placeholder="Choose a page", max_values=1))

        player_results = []
        for count, player in enumerate(players):
            player: StatsPlayer
            player_results.append(disnake.SelectOption(label=f"{player.name}", emoji=self.bot.fetch_emoji(player.town_hall).partial_emoji, value=f"{count}"))
        row_two = disnake.ui.ActionRow(disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1))


        embed = await detailed_player_board(bot=self.bot, custom_player=player, server=ctx.guild)
        await ctx.send(embed=embed, components=[row_one, row_two])'''

        if player is None and discord_user is None:
            discord_user = ctx.author
            search_query = str(ctx.author.id)
        elif player is not None:
            search_query = player.tag
        else:
            search_query = str(discord_user.id)
        results = await search_results(self.bot, search_query)
        results = results[:25]
        if not results:
            raise MessageException(f"{discord_user.name} has no accounts linked.")

        msg = await ctx.original_message()
        await button_pagination(self.bot, ctx, msg, results)


    @player.sub_command(name="upgrades", description="Show upgrades left for an account")
    async def upgrades(self, ctx: disnake.ApplicationCommandInteraction,
                       player_tag: str = None,
                       discord_user: disnake.Member = None):
        raise MessageException("Command under construction")
        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

        player = await self.bot.getPlayer(player_tag=player_tag, custom=True, raise_exceptions=True)
        embed = await create_profile_troops(bot=self.bot, result=player)
        components = []
        '''if len(players) > 1:
            player_results = []
            for count, player in enumerate(players):
                player_results.append(
                    disnake.SelectOption(label=f"{player.name}", emoji=player.town_hall_cls.emoji.partial_emoji,
                                         value=f"{count}"))
            profile_select = disnake.ui.Select(options=player_results, placeholder="Accounts", max_values=1)
            st2 = disnake.ui.ActionRow()
            st2.append_item(profile_select)
            components = [st2]'''
        await ctx.send(embeds=embed, components=components)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break

            await res.response.defer()
            current_page = int(res.values[0])
            embed = await create_profile_troops(self.bot, players[current_page])
            await res.edit_original_message(embeds=embed)


    @player.sub_command(name="accounts", description="List of accounts a user has & combined stats")
    async def accounts(self, ctx: disnake.ApplicationCommandInteraction,
                   discord_user: disnake.Member = None):
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        discord_user = discord_user or ctx.author

        embed = await player_accounts(bot=self.bot, discord_user=discord_user, embed_color=embed_color)

        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(
                label="", emoji=self.bot.emoji.refresh.partial_emoji,
                style=disnake.ButtonStyle.grey, custom_id=f"playeraccounts:{discord_user.id}"))

        await ctx.edit_original_message(embed=embed, components=buttons)



    @player.sub_command(name="to-do", description="Get a list of things to be done (war attack, legends hits, capital raids etc)")
    async def to_do(self, ctx: disnake.ApplicationCommandInteraction,
                    discord_user: disnake.Member = None):

        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=ctx.guild_id)
        discord_user = discord_user or ctx.author

        buttons = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="", emoji=self.bot.emoji.refresh.partial_emoji,
                    style=disnake.ButtonStyle.grey, custom_id=f"playertodo:{discord_user.id}"),
                disnake.ui.Button(
                    label="", emoji=self.bot.emoji.gear.partial_emoji,
                    style=disnake.ButtonStyle.grey, custom_id=f"playertodosettings:ctx"
                ))
        embed = await to_do_embed(bot=self.bot, discord_user=discord_user, embed_color=embed_color)
        await ctx.edit_original_message(embed=embed, components=buttons)


    '''@player.sub_command(name="war-stats", description="War stats of a player or discord user")
    async def war_stats_player(self, ctx: disnake.ApplicationCommandInteraction,
                               player_tag: str = None,
                               discord_user: disnake.Member = None,
                               start_date=0,
                               end_date=9999999999):
        """
            Parameters
            ----------
            player_tag: (optional) player to view war stats on
            discord_user: (optional) discord user's accounts to view war stats of
            start_date: (optional) filter stats by date, default is to view this season
            end_date: (optional) filter stats by date, default is to view this season
        """
        if start_date != 0 and end_date != 9999999999:
            start_date = int(datetime.strptime(start_date, "%d %B %Y").timestamp())
            end_date = int(datetime.strptime(end_date, "%d %B %Y").timestamp())
        else:
            start_date = int(coc.utils.get_season_start().timestamp())
            end_date = int(coc.utils.get_season_end().timestamp())

        if player_tag is None and discord_user is None:
            search_query = str(ctx.author.id)
        elif player_tag is not None:
            search_query = player_tag
        else:
            search_query = str(discord_user.id)

        players = (await search_results(self.bot, search_query))[:25]
        if not players:
            embed = disnake.Embed(description="**No matching player/discord user found**", colour=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await player_embeds.create_player_hr(bot=self.bot, player=players[0], start_date=start_date, end_date=end_date)
        await ctx.edit_original_message(embed=embed, components=player_components(players))
        if len(players) == 1:
            return
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break
            await res.response.defer()
            page = int(res.values[0])
            embed = await player_embeds.create_player_hr(bot=self.bot, player=players[page], start_date=start_date, end_date=end_date)
            await res.edit_original_message(embed=embed)


    @player.sub_command(name="stats", description="Get stats for different areas of a player")
    async def player_stats(self, ctx: disnake.ApplicationCommandInteraction,
                           member: disnake.Member,
                           type:str =commands.Param(choices=["CWL", "Raids"])):
        if type == "Raids":
            return await player_embeds.raid_stalk(bot=self.bot, ctx=ctx, member=member)
        elif type == "CWL":
            return await player_embeds.cwl_stalk(bot=self.bot,ctx=ctx, member=member)'''



def setup(bot: CustomClient):
    bot.add_cog(PlayerCommands(bot))