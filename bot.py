import discord
from discord import app_commands
import json
import time
import os.path
from discord.ext import commands, tasks
from asyncio import sleep
import env

intents = discord.Intents.all()

# bot = commands.Bot(intents=intents,command_prefix='>', help_command=None, status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name="everyone"))

bot = discord.Client(intents=intents)

days_of_week = {'monday': '0', 'tuesday': '1', 'wednesday': '2', 'thursday': '3', 'friday': '4', 'saturday': '5', 'sunday': '6'}

# helper methods
def has_perms(guild: discord.Guild, user: discord.Member):

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

def get_guild_file(guild: discord.Guild):
    return 'Guilds/' + str(guild.id) + '.json'

async def create_guild_json(guild: discord.Guild):
    f = open(get_guild_file(guild), 'w')
    default_data = {'utc_offset': '+00', 'perms_role': 'Add Notis', 'notifications': []}
    f.write(json.dumps(default_data, indent=2))
    f.close()


def getIds():
    ids = []
    for guild in bot.guilds:
        ids.append(guild.id)
    
    return ids

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

                pings = ''
                for ping in noti['pings']:
                    pings += '@'
                    pings += ping

                await bot.get_channel(noti['channel_id']).send(pings ,embed=msg)
        f.close()

@bot.event
async def on_guild_join(guild: discord.Guild):
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
def on_help(command: str):
    em = discord.Embed()
    f = open('command_help_info.json')
    command_info: dict = json.load(f)
    if command == '':
        cmds = ''
        for cmd in command_info:
            cmds += ' - '
            cmds += cmd
            cmds += '\n'
        em.add_field(name='Commands', value=cmds, inline=False)
    else:
        if command in command_info:
            em.add_field(name='Command: ' + command, value=command_info[command], inline=False)
        else:
            em.add_field(name='Command: ' + command, value='command not found', inline=False)

    f.close()
    return em

async def on_now(guild: discord.Guild):

    f = open(get_guild_file(guild))
    data = json.load(f)
    f.close()

    hour_offset = int(data['utc_offset'][1:3])

    if data['utc_offset'][0] == '-':
        hour_offset = -hour_offset

    guild_time =  time.gmtime(time.time() + hour_offset*60*60)

    em = discord.Embed()
    em.add_field(name="Time now", value=time.strftime('%Y-%m-%d %H:%M', guild_time), inline=False)

    return em

async def on_list(guild: discord.Guild, channel: discord.TextChannel, all: bool):
    f = open(get_guild_file(guild))
    data = json.load(f)

    msg = ''

    for noti in data['notifications']:
        if noti['channel_id'] == channel.id or all:
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
            
    f.close()

    if msg == '':
        msg = 'No notifications'

    em = discord.Embed()
    em.add_field(name='Notifications', value=msg, inline=False)
    return em

async def on_set_utc_offset(guild: discord.Guild, author: discord.Member, offset: str):

    if not has_perms(guild, author):
        em = discord.Embed()
        em.add_field(name='Set_utc_offset', value='You have no permissions to use this command')
        return em

    if len(offset) !=  3 or (offset[0] != '+' and offset[0] != '-'):
        em = discord.Embed()
        em.add_field(name='Set_utc_offset', value='Invalid format')
        return em
    if int(offset[1:3]) > (14 if offset[0] == '+' else 12):
        em = discord.Embed()
        em.add_field(name='Set_utc_offset', value='Invalid offset, range is -12 to +14')
        return em

    f = open(get_guild_file(guild))
    data = json.load(f)
    f.close()

    data['utc_offset'] = offset

    f = open(get_guild_file(guild), 'w')
    f.write(json.dumps(data, indent=2))
    f.close()

    em = discord.Embed()
    em.add_field(name='UTC offset', value='UTC offset is now **' + offset + ':00**')

    return em

async def on_set_perms_role(guild: discord.Guild, author: discord.Member, role_name: str):

    if not has_perms(guild, author):
        em = discord.Embed()
        em.add_field(name='Set_perms_role', value='You have no permissions to use this command')
        return em

    f = open(get_guild_file(guild))
    data = json.load(f)
    f.close()

    data['perms_role'] = role_name

    f = open(get_guild_file(guild), 'w')
    f.write(json.dumps(data, indent=2))
    f.close()

    em = discord.Embed()
    em.add_field(name='Permission Role', value='Role with perms is now: **' + role_name + '**')

    return em

# adds notification info to guild json
async def on_add(guild: discord.Guild, author: discord.Member, channel: discord.TextChannel, 
pings: str, msg: str, day: str, time: str):
    if not os.path.exists(get_guild_file(guild)):
        create_guild_json(guild)

    f = open(get_guild_file(guild))
    data = json.load(f)

    if not has_perms(guild, author):
        em = discord.Embed()
        em.add_field(name='Add', value='You have no permissions to use this command')
        return em

    day = day.lower()
    
    # check invalid inputs for command
    if len(time) != 5 or time[2] != ':':
        em = discord.Embed()
        em.add_field(name='Add', value='Invalid format')
        return em
    if int(time[0:2]) > 23 or int(time[3:5]) > 59:
        em = discord.Embed()
        em.add_field(name='Add', value='Invalid time')
        return em
    
    if day not in days_of_week:
        em = discord.Embed()
        em.add_field(name='Add', value='Invalid day of week')
        return em

    noti = {
        'pings': pings.split(' ') if len(pings) != 0 else [],
        'message': msg,
        'day_of_week': days_of_week[day],
        'time': time,
        'channel_id': channel.id
    }

    f.close()

    data['notifications'] += [noti]

    f = open(get_guild_file(guild), 'w')
    f.write(json.dumps(data, indent=2))
    f.close()

    em = discord.Embed()
    em.add_field(name='Notification', value='Notification added to go off **' + day.capitalize() + ', ' + time + '**')

    return em

async def on_remove(guild: discord.Guild, author: discord.Member, noti: str):

    if not has_perms(guild, author):
        em = discord.Embed()
        em.add_field(name='Remove', value='You have no permissions to use this command')
        return em

    f = open(get_guild_file(guild))
    data = json.load(f)
    f.close()

    em = discord.Embed()

    for guild_noti in data['notifications']:
        if guild_noti['message'] == noti:
            data['notifications'].remove(guild_noti)
            f = open(get_guild_file(guild), 'w')
            f.write(json.dumps(data, indent=2))
            f.close()
            em.add_field(name='Notification', value='notifications: ' + noti + 'has been removed')
            return em

    em.add_field(name='Notification', value='Notification at ____ does not exist')
    return em

#name='woah',
#description='woajsodj',
# @tree.command(guild=discord.Object(id=961988797422248057))
# async def test(interaction: discord.Interaction): #, number: int, string: str):
#     await interaction.response.send_message('woajsodaj')


tree = app_commands.CommandTree(client=bot)

@tree.command()
async def list(interaction: discord.Interaction, all: str):
    await interaction.response.send_message(embed=on_list(interaction.guild, interaction.channel, True if all == 'all' else False))

@tree.command()
async def help(interaction: discord.Interaction, command: str):
    await interaction.response.send_message(embed=on_help(command))

@tree.command()
async def add(interaction: discord.Interaction, pings: str, message: str, day: str, time: str):
    await interaction.response.send_message(embed=on_add(interaction.guild, interaction.user, interaction.channel, pings, message, day, time))

@tree.command()
async def remove(interaction: discord.Interaction, noti: str):
    await interaction.response.send_message(embed=on_remove(interaction.guild, interaction.user, noti))

@tree.command()
async def set_utc_offset(interaction: discord.Interaction, offset: str):
    await interaction.response.send_message(embed=on_set_utc_offset(interaction.guild, interaction.user, offset))

@tree.command()
async def set_perms_role(interaction: discord.Interaction, role_name: str):
    await interaction.response.send_message(embed=on_set_perms_role(interaction.guild, interaction.user, role_name))

@tree.command()
async def now(interaction: discord.Interaction):
    await interaction.response.send_message(embed=on_now(interaction.guild))

def main():
    bot.run(env.token)

if __name__ == '__main__':
    main()
