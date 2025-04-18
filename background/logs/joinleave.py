import ast

import coc
import disnake
from disnake.ext import commands

from background.logs.events import clan_ee
from classes.bot import CustomClient
from classes.DatabaseClient.Classes.settings import DatabaseClan
from exceptions.CustomExceptions import MissingWebhookPerms
from utility.clash.other import basic_heros, leagueAndTrophies
from utility.discord_utils import get_webhook_for_channel
from commands.bans.utils import add_ban

class join_leave_events(commands.Cog, name='Clan Join & Leave Events'):
    def __init__(self, bot: CustomClient):
        self.bot = bot
        self.clan_ee = clan_ee
        self.clan_ee.on('members_join_leave', self.player_join_leave)

    async def player_join_leave(self, event):
        clan = coc.Clan(data=event['new_clan'], client=self.bot.coc_client)

        if members_joined := event.get('joined', []):
            tracked = await self.bot.clan_db.find({'$and': [{'tag': clan.tag}, {'logs.join_log.webhook': {'$ne': None}}]}).to_list(length=None)
            if tracked:
                members_joined = [coc.ClanMember(data=member, client=self.bot.coc_client, clan=clan) for member in members_joined]
                player_pull = await self.bot.get_players(tags=[m.tag for m in members_joined], use_cache=False, custom=False)
                player_map = {p.tag: p for p in player_pull}

                embeds = []
                players = []
                for member in members_joined:
                    player = player_map.get(member.tag)
                    if player is None:
                        continue
                    players.append(player)
                    hero = basic_heros(bot=self.bot, player=player)

                    th_emoji = self.bot.fetch_emoji(player.town_hall)
                    embed = disnake.Embed(
                        description=f'[**{player.name}** ({player.tag})]({player.share_link})\n'
                        + f'**{th_emoji}{player.town_hall}{leagueAndTrophies(bot=self.bot, player=player)}{self.bot.emoji.war_star}{player.war_stars}{hero}**\n',
                        color=disnake.Color.green(),
                    )
                    embed.set_footer(
                        icon_url=clan.badge.url,
                        text=f'Joined {clan.name} [{clan.member_count}/50]',
                    )
                    embeds.append(embed)
                embeds = [embeds[i : i + 10] for i in range(0, len(embeds), 10)]

                components = []
                if len(players) >= 2:
                    options = []
                    for account in players:
                        options.append(
                            disnake.SelectOption(
                                label=account.name,
                                emoji=self.bot.fetch_emoji(name=account.town_hall).partial_emoji,
                                value=f'ticketviewer_{account.tag}',
                            )
                        )
                    select = disnake.ui.Select(
                        options=options,
                        placeholder='Account Info',
                        min_values=1,  # the minimum number of options a user must select
                        max_values=1,  # the maximum number of options a user can select
                    )
                    components = [disnake.ui.ActionRow(select)]
                elif len(players) == 1:
                    components = [
                        disnake.ui.ActionRow(
                            disnake.ui.Button(
                                label='',
                                emoji=self.bot.emoji.user_search.partial_emoji,
                                style=disnake.ButtonStyle.grey,
                                custom_id=f'redditplayer_{players[0].tag}',
                            )
                        )
                    ]

                for cc in tracked:
                    db_clan = DatabaseClan(bot=self.bot, data=cc)
                    if db_clan.server_id not in self.bot.OUR_GUILDS:
                        continue

                    if not embeds:
                        continue

                    log = db_clan.join_log

                    try:
                        webhook = await self.bot.getch_webhook(log.webhook)
                        if webhook.user.id != self.bot.user.id:
                            webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                            await log.set_webhook(id=webhook.id)
                        if log.thread is not None:
                            thread = await self.bot.getch_channel(log.thread)
                            if thread.locked:
                                continue
                            for embed_chunk in embeds:
                                await webhook.send(
                                    embeds=embed_chunk,
                                    thread=thread,
                                    components=components if log.profile_button else None,
                                )
                        else:
                            for embed_chunk in embeds:
                                await webhook.send(embeds=embed_chunk, components=components if log.profile_button else None)
                    except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                        await log.set_thread(id=None)
                        await log.set_webhook(id=None)
                        continue

        if members_left := event.get('left', []):
            tracked = await self.bot.clan_db.find({'$and': [{'tag': clan.tag}, {'logs.leave_log.webhook': {'$ne': None}}]}).to_list(length=None)
            if tracked:
                members_left = [coc.ClanMember(data=member, client=self.bot.coc_client, clan=clan) for member in members_left]
                player_pull = await self.bot.get_players(tags=[m.tag for m in members_left], use_cache=False, custom=False)
                player_map = {p.tag: p for p in player_pull}

                embeds = []
                for member in members_left:
                    player = player_map.get(member.tag)
                    if player is None:
                        continue
                    th_emoji = self.bot.fetch_emoji(player.town_hall)
                    embed = disnake.Embed(
                        description=f'[**{player.name}** ({player.tag})]({player.share_link})\n'
                        + f'{th_emoji}**{player.town_hall}{leagueAndTrophies(bot=self.bot, player=player)}(#{member.clan_rank})**'
                        +  f'{self.bot.emoji.up_green_arrow}**{player.donations}**{self.bot.emoji.down_red_arrow}**{player.received}**'
                        +  f'{self.bot.emoji.pin}**{member.role.in_game_name}**\n',
                        color=disnake.Color.red(),
                    )
                    if player.clan is not None and player.clan.tag != clan.tag:
                        embed.set_footer(
                            icon_url=player.clan.badge.url,
                            text=f'Left {clan.name} [{clan.member_count}/50] and Joined {player.clan.name}',
                        )
                    else:
                        embed.set_footer(
                            icon_url=clan.badge.url,
                            text=f'Left {clan.name} [{clan.member_count}/50]',
                        )
                    embeds.append(embed)
                embeds = [embeds[i : i + 10] for i in range(0, len(embeds), 10)]

                for cc in tracked:
                    db_clan = DatabaseClan(bot=self.bot, data=cc)
                    if db_clan.server_id not in self.bot.OUR_GUILDS:
                        continue

                    if not embeds:
                        continue

                    log = db_clan.leave_log

                    components = []
                    if log.ban_button or log.strike_button:
                        stat = []
                        if log.ban_button:
                            stat += [
                                disnake.ui.Button(
                                    label='Ban',
                                    emoji='🔨',
                                    style=disnake.ButtonStyle.red,
                                    custom_id=f'jlban_{player.tag}',
                                )
                            ]
                        if log.strike_button:
                            stat += [
                                disnake.ui.Button(
                                    label='Strike',
                                    emoji='✏️',
                                    style=disnake.ButtonStyle.grey,
                                    custom_id=f'jlstrike_{player.tag}',
                                )
                            ]
                        buttons = disnake.ui.ActionRow()
                        for button in stat:
                            buttons.append_item(button)
                        components = [buttons]
                    try:
                        webhook = await self.bot.getch_webhook(log.webhook)
                        if webhook.user.id != self.bot.user.id:
                            webhook = await get_webhook_for_channel(bot=self.bot, channel=webhook.channel)
                            await log.set_webhook(id=webhook.id)
                        if log.thread is not None:
                            thread = await self.bot.getch_channel(log.thread)
                            if thread.locked:
                                continue
                            for embed_chunk in embeds:
                                await webhook.send(
                                    embeds=embed_chunk,
                                    thread=thread,
                                    components=components,
                                )
                        else:
                            for embed_chunk in embeds:
                                await webhook.send(embeds=embed_chunk, components=components)
                    except (disnake.NotFound, disnake.Forbidden, MissingWebhookPerms):
                        await log.set_thread(id=None)
                        await log.set_webhook(id=None)
                        continue

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        if 'jlban_' in ctx.data.custom_id:
            check = await self.bot.white_list_check(ctx, 'ban add')
            if not check and not ctx.author.guild_permissions.manage_guild:
                await ctx.send(
                    content='You cannot use this component. Missing Permissions.',
                    ephemeral=True,
                )
            player = ctx.data.custom_id.split('_')[-1]
            player = await self.bot.getPlayer(player_tag=player)
            components = [
                disnake.ui.TextInput(
                    label=f'Reason to ban {player.name}',
                    placeholder='Ban Reason (i.e. missed 25 war attacks)',
                    custom_id=f'ban_reason',
                    required=True,
                    style=disnake.TextInputStyle.single_line,
                    max_length=100,
                )
            ]
            await ctx.response.send_modal(title='Ban Form', custom_id='banform-', components=components)

            def check(res):
                return ctx.author.id == res.author.id

            try:
                modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                    'modal_submit',
                    check=check,
                    timeout=300,
                )
            except:
                return

            # await modal_inter.response.defer()
            ban_reason = modal_inter.text_values['ban_reason']
            embed = await add_ban(bot=self.bot, player=player, added_by=ctx.user, guild=ctx.guild, reason=ban_reason, rollover_days=None, dm_player=None)
            await modal_inter.send(embed=embed)

        if 'jlstrike_' in ctx.data.custom_id:
            check = await self.bot.white_list_check(ctx, 'strike add')
            if not check and not ctx.author.guild_permissions.manage_guild:
                await ctx.send(
                    content='You cannot use this component. Missing Permissions.',
                    ephemeral=True,
                )
            player = ctx.data.custom_id.split('_')[-1]
            player = await self.bot.getPlayer(player_tag=player)
            components = [
                disnake.ui.TextInput(
                    label=f'Reason for strike on {player.name}',
                    placeholder='Strike Reason (i.e. low donation ratio)',
                    custom_id=f'strike_reason',
                    required=True,
                    style=disnake.TextInputStyle.single_line,
                    max_length=100,
                ),
                disnake.ui.TextInput(
                    label=f'Rollover Days',
                    placeholder='In how many days you want this to expire',
                    custom_id=f'rollover_days',
                    required=False,
                    style=disnake.TextInputStyle.single_line,
                    max_length=3,
                ),
                disnake.ui.TextInput(
                    label=f'Strike Weight',
                    placeholder='Weight you want for this strike (default is 1)',
                    custom_id=f'strike_weight',
                    required=False,
                    style=disnake.TextInputStyle.single_line,
                    max_length=2,
                ),
            ]
            await ctx.response.send_modal(title='Strike Form', custom_id='strikeform-', components=components)

            def check(res):
                return ctx.author.id == res.author.id

            try:
                modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                    'modal_submit',
                    check=check,
                    timeout=300,
                )
            except:
                return

            # await modal_inter.response.defer()
            strike_reason = modal_inter.text_values['strike_reason']
            rollover_days = modal_inter.text_values['rollover_days']
            if rollover_days != '':
                if not str(rollover_days).isdigit():
                    return await modal_inter.send(content='Rollover Days must be an integer', ephemeral=True)
                else:
                    rollover_days = int(rollover_days)
            else:
                rollover_days = None
            strike_weight = modal_inter.text_values['strike_weight']
            if strike_weight != '':
                if not str(strike_weight).isdigit():
                    return await modal_inter.send(content='Strike Weight must be an integer', ephemeral=True)
                else:
                    strike_weight = int(strike_weight)
            else:
                strike_weight = 1
            strike_cog = self.bot.get_cog(name='Strikes')
            embed = await strike_cog.strike_player(ctx, player, strike_reason, rollover_days, strike_weight)
            await modal_inter.send(embed=embed)


def setup(bot: CustomClient):
    bot.add_cog(join_leave_events(bot))
