import discord
import time
from discord.ext import commands, tasks
from asyncio import sleep
import env
import database

bot = commands.Bot(command_prefix='>', help_command=None, status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name=">help"))

days_of_week = {'monday': '0', 'tuesday': '1', 'wednesday': '2', 'thursday': '3', 'friday': '4', 'saturday': '5', 'sunday': '6'}

# helper methods
def has_perms(guild: discord.Guild, user: discord.Member):

    data = database.get_guild_json(guild.id)

    if user.guild_permissions.administrator or user.guild_permissions.manage_guild:
        return True
    else:
        for role in user.roles:
            if role.name == data['perms_role']:
                return True
        
    return False

def create_guild_json(guild):
    default_data = {'_id': guild.id, 'utc_offset': '+00', 'perms_role': 'Add Notis', 'notifications': []}
    database.create_guild_json(default_data)


# bot event and updates

# updates
@tasks.loop(seconds=0.5)
async def update_task():
    while True:
        if time.gmtime().tm_sec <= 5: # update every start of minute
            await check_notifications()
            await sleep(20)
        await sleep(0.5)

async def check_notifications():

    for guild in bot.guilds:
        if not database.get_guild_json(guild.id):
            create_guild_json(guild)

        data = database.get_guild_json(guild.id)
        hour_offset = int(data['utc_offset'][1:3])

        if data['utc_offset'][0] == '-':
            hour_offset = -hour_offset

        guild_time = time.gmtime(time.time() + hour_offset*60*60)

        for noti in data['notifications']:
            if noti['day_of_week'] == str(guild_time.tm_wday) and noti['time'] == time.strftime('%H:%M', guild_time):
                msg = discord.Embed()
                msg.add_field(name=noti['message'], value=time.strftime('%Y-%m-%d %H:%M', guild_time), inline=False)

                pings = ''
                for ping in noti['pings']:
                    pings += '@'
                    pings += ping

                await bot.get_channel(noti['channel_id']).send(pings ,embed=msg)

@bot.event
async def on_guild_join(guild: discord.Guild):
    # create guild file and roles on join
    print('joined', guild)
    if not database.get_guild_json(guild.id):
        await create_guild_json(guild)
        await guild.create_role(name='Add Notis')

    # welcome message    
    em = discord.Embed()
    em.add_field(name='RHS Bot', value='This is a discord bot for reminders, use **' + bot.command_prefix + 
    'set_utc_offset** to set the timezone of the server, use **' + bot.command_prefix + 'help** for more info.')
    if guild.system_channel:
        await guild.system_channel.send(embed=em)
    else:
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel) and channel.name == 'general':
                await channel.send(embed=em)
                break

@bot.event
async def on_ready():
    print('running at', time.ctime(time.time()))
    print('Servers (guilds): ')
    for guild in bot.guilds:
        print(' - ' + guild.name + ' id: ' + str(guild.id))

    update_task.before_loop(bot.wait_until_ready)
    update_task.start()


# commands 

@bot.command()
async def help(ctx: commands.Context, *args):
    em = discord.Embed()
    if len(args) == 0:
        cmds = ''
        for cmd in bot.commands:
            cmds += ' - '
            cmds += cmd.name
            cmds += '\n'
        cmds += '\n'
        em.add_field(name='Commands', value=cmds+bot.command_prefix+'help (commmand) for more info', inline=False)
    else:
        desc = database.get_command_info(args[0])
        if desc:
            em.add_field(name='Command: ' + args[0], value=desc, inline=False)
        else:
            em.add_field(name='Command: ' + args[0], value='command not found', inline=False)

    await ctx.send(embed=em)

@bot.command()
async def now(ctx: commands.Context):

    data = database.get_guild_json(ctx.guild.id)

    hour_offset = int(data['utc_offset'][1:3])

    if data['utc_offset'][0] == '-':
        hour_offset = -hour_offset

    guild_time = time.gmtime(time.time() + hour_offset*60*60)

    em = discord.Embed()
    em.add_field(name="Time now", value=time.strftime('%Y-%m-%d %H:%M', guild_time), inline=False)

    await ctx.send(embed=em)

@bot.command()
async def list(ctx: commands.Context, *args):
    data = database.get_guild_json(ctx.guild.id)

    msg = ''

    for noti in data['notifications']:
        if noti['channel_id'] == ctx.channel.id or len(args) > 0 and args[0] == 'all':
            msg += ' - '
            msg += noti['message']
            msg += ' ('
            for day, num in days_of_week.items():
                if num == noti['day_of_week']:
                    msg += day.capitalize()
            msg += ' '
            msg += noti['time']
            msg += ')'
            msg += '\n'
            
    if msg == '':
        msg = 'No notifications'

    em = discord.Embed()
    em.add_field(name='Notifications', value=msg, inline=False)
    await ctx.send(embed=em)

@bot.command()
async def set_utc_offset(ctx: commands.Context, offset: str):

    if not has_perms(ctx.guild, ctx.author):
        em = discord.Embed()
        em.add_field(name='Set_utc_offset', value='You have no permissions to use this command')
        await ctx.send(embed=em)
        return

    if len(offset) !=  3 or (offset[0] != '+' and offset[0] != '-'):
        em = discord.Embed()
        em.add_field(name='Set_utc_offset', value='Invalid format')
        await ctx.send(embed=em)
        return
    if int(offset[1:3]) > (14 if offset[0] == '+' else 12):
        em = discord.Embed()
        em.add_field(name='Set_utc_offset', value='Invalid offset, range is -12 to +14')
        await ctx.send(embed=em)
        return

    data = database.get_guild_json(ctx.guild.id)

    data['utc_offset'] = offset

    database.write_guild_json(ctx.guild.id, data)

    em = discord.Embed()
    em.add_field(name='UTC offset', value='UTC offset is now **' + offset + ':00**')

    await ctx.send(embed=em)

@bot.command()
async def set_perms_role(ctx: commands.Context, role_name: str):

    if not has_perms(ctx.guild, ctx.author):
        em = discord.Embed()
        em.add_field(name='Set_perms_role', value='You have no permissions to use this command')
        await ctx.send(embed=em)
        return

    data = database.get_guild_json(ctx.guild.id)

    data['perms_role'] = role_name

    database.write_guild_json(ctx.guild.id, data)

    em = discord.Embed()
    em.add_field(name='Permission Role', value='Role with perms is now: **' + role_name + '**')

    await ctx.send(embed=em)

# adds notification info to guild json
@bot.command()
async def add(ctx: commands.Context, pings: str, msg: str, day: str, time: str):
    if not database.get_guild_json(ctx.guild.id):
        create_guild_json(ctx.guild)

    data = database.get_guild_json(ctx.guild.id)

    if not has_perms(ctx.guild, ctx.author):
        em = discord.Embed()
        em.add_field(name='Add', value='You have no permissions to use this command')
        await ctx.send(embed=em)
        return

    day = day.lower()
    
    # check invalid inputs for command
    if len(time) != 5 or time[2] != ':':
        em = discord.Embed()
        em.add_field(name='Add', value='Invalid format')
        await ctx.send(embed=em)
        return
    if int(time[0:2]) > 23 or int(time[3:5]) > 59:
        em = discord.Embed()
        em.add_field(name='Add', value='Invalid time')
        await ctx.send(embed=em)
        return 
    
    if day not in days_of_week:
        em = discord.Embed()
        em.add_field(name='Add', value='Invalid day of week')
        await ctx.send(embed=em)
        return 

    noti = {
        'pings': pings.split(' ') if len(pings) != 0 else [],
        'message': msg,
        'day_of_week': days_of_week[day],
        'time': time,
        'channel_id': ctx.channel.id
    }

    data['notifications'] += [noti]

    database.write_guild_json(ctx.guild.id, data)

    em = discord.Embed()
    em.add_field(name='Notification', value='Notification added to go off **' + day.capitalize() + ', ' + time + '**')

    await ctx.send(embed=em)

@bot.command()
async def remove(ctx: commands.Context, noti: str):

    if not has_perms(ctx.guild, ctx.author):
        em = discord.Embed()
        em.add_field(name='Remove', value='You have no permissions to use this command')
        await ctx.send(embed=em)
        return

    data = database.get_guild_json(ctx.guild.id)

    em = discord.Embed()

    for guild_noti in data['notifications']:
        if guild_noti['message'] == noti:
            data['notifications'].remove(guild_noti)
            database.write_guild_json(ctx.guild.id, data)
            em.add_field(name='Notification', value='notifications: ' + noti + 'has been removed')
            await ctx.send(embed=em)
            return

    em.add_field(name='Notification', value='Notification at ____ does not exist')
    await ctx.send(embed=em)


def main():
    bot.run(env.DISCORD_BOT_TOKEN)

if __name__ == '__main__':
    main()
