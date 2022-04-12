import discord
import json
import time
import os.path
from discord.ext import commands, tasks
from asyncio import sleep
# import env

bot = commands.Bot(command_prefix='>', help_command=None, status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name="everyone"))

days_of_week = {'monday': '0', 'tuesday': '1', 'wednesday': '2', 'thursday': '3', 'friday': '4', 'saturday': '5', 'sunday': '6'}

# helper methods
def has_perms(guild, user):

    f = open(get_guild_file(guild))

    data = json.load(f)

    f.close()

    if user.guild_permissions.administrator:
        return True
    else:
        for role in user.roles:
            if role.name == data['perms_role']:
                return True
        
    return False

def get_guild_file(guild):
    return 'Guilds/' + str(guild.id) + '.json'

async def create_guild_json(guild):
    f = open(get_guild_file(guild), 'w')
    default_data = {'utc_offset': '+00', 'perms_role': 'Add Notis', 'notifications': []}
    f.write(json.dumps(default_data, indent=2))
    f.close()


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
        if not os.path.exists(get_guild_file(guild)):
            await create_guild_json(guild)
            continue
        f = open(get_guild_file(guild))
        data = json.load(f)
        hour_offset = int(data['utc_offset'][1:3])

        if data['utc_offset'][0] == '-':
            hour_offset = -hour_offset

        guild_time = time.gmtime(time.time() + hour_offset*60*60)

        for noti in data['notifications']:
            if noti['day_of_week'] == str(guild_time.tm_wday) and noti['time'] == time.strftime('%H:%M', guild_time):
                msg = discord.Embed()
                msg.add_field(name=noti['message'], value=time.strftime('%Y-%m-%d %H:%M', guild_time), inline=False)

                await bot.get_channel(noti['channel_id']).send(embed=msg)
        f.close()

@bot.event
async def on_guild_join(guild):
    # create guild file and roles on join
    print('joined', guild)
    if not os.path.exists(get_guild_file(guild)):
        await create_guild_json(guild)
        await guild.create_role(name='Add Notis')

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
async def help(ctx, *args):
    em = discord.Embed()
    if len(args) == 0:
        cmds = ''
        for cmd in bot.commands:
            cmds += ' - '
            cmds += cmd.name
            cmds += '\n'
        em.add_field(name='Commands', value=cmds, inline=False)
    else:
        f = open('command_help_info.json')
        command_info = json.load(f)
        if args[0] in command_info:
            em.add_field(name='Command: ' + args[0], value=command_info[args[0]], inline=False)
        else:
            em.add_field(name='Command: ' + args[0], value='command not found', inline=False)
        f.close()

    await ctx.send(embed=em)

@bot.command()
async def now(ctx):

    f = open(get_guild_file(ctx.guild))
    data = json.load(f)
    f.close()

    hour_offset = int(data['utc_offset'][1:3])

    if data['utc_offset'][0] == '-':
        hour_offset = -hour_offset

    guild_time =  time.gmtime(time.time() + hour_offset*60*60)

    em = discord.Embed()
    em.add_field(name="Time now", value=time.strftime('%Y-%m-%d %H:%M', guild_time), inline=False)

    await ctx.send(embed=em)

@bot.command()
async def list(ctx, *args):
    f = open(get_guild_file(ctx.guild))
    data = json.load(f)

    msg = ''

    if len(args) == 0 or args[0] != 'all':
        for noti in data['notifications']:
            if noti['channel_id'] == ctx.channel.id:
                msg += ' - '
                msg += noti['message']
                msg += '\n'
    else:
        for noti in data['notifications']:
            msg += ' - '
            msg += noti['message']
            msg += '\n'
            
    f.close()

    if msg == '':
        msg = 'No notifications'

    em = discord.Embed()
    em.add_field(name='Notifications', value=msg, inline=False)
    await ctx.send(embed=em)

@bot.command()
async def set_utc_offset(ctx, offset):

    if not has_perms(ctx.guild, ctx.author):
        await ctx.send('no perms to use command set_utc_offset')
        return

    if len(offset) !=  3 or (offset[0] != '+' and offset[0] != '-'):
        await ctx.send('invalid format')
        return
    if int(offset[1:3]) > (14 if offset[0] == '+' else 12):
        await ctx.send('invalid offset')
        return

    f = open(get_guild_file(ctx.guild))
    data = json.load(f)
    f.close()

    data['utc_offset'] = offset

    f = open(get_guild_file(ctx.guild), 'w')
    f.write(json.dumps(data, indent=2))
    f.close()

    await ctx.send('UTC offset is now ' + offset + ':00')

@bot.command()
async def set_perms_role(ctx, role_name):

    if not has_perms(ctx.guild, ctx.author):
        await ctx.send('no perms to use command set_perms_role')
        return

    f = open(get_guild_file(ctx.guild))
    data = json.load(f)
    f.close()

    data['perms_role'] = role_name

    f = open(get_guild_file(ctx.guild), 'w')
    f.write(json.dumps(data, indent=2))
    f.close()
    await ctx.send('permission for perms is set to ' + role_name)

# adds notification info to guild json
@bot.command()
async def add(ctx, msg, day, time):
    if not os.path.exists(get_guild_file(ctx.guild)):
        create_guild_json(ctx.guild)

    f = open(get_guild_file(ctx.guild))
    data = json.load(f)

    if not has_perms(ctx.guild, ctx.author):
        await ctx.send('no perms to use add')
        return

    day = day.lower()
    
    # check invalid inputs for command
    if len(time) != 5 or time[2] != ':':
        await ctx.send('wrong format')
        return
    if int(time[0:2]) > 23 or int(time[3:5]) > 59:
        await ctx.send('invalid time')
        return 
    
    if day not in days_of_week:
        await ctx.send('invalid day of week')
        return 

    noti = {
        'message': msg,
        'day_of_week': days_of_week[day],
        'time': time,
        'channel_id': ctx.channel.id
    }

    f.close()

    data['notifications'] += [noti]

    f = open(get_guild_file(ctx.guild), 'w')
    f.write(json.dumps(data, indent=2))
    f.close()
    await ctx.send('Notification Added')
    print('notification added')

@bot.command()
async def remove(ctx):
    await ctx.send('?c CANt remove')


def main():
    # token here because doesnt matter rn
    bot.run('OTYxNzU5ODUxODMzMzU2Mjk4.Yk9qqQ.Cp-RSjOzlRByBdj36F0hXRIknTw')
    # bot.run(env.token)

if __name__ == '__main__':
    main()
