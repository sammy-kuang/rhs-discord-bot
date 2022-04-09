import discord
import json
import time
import env
from discord.ext import commands, tasks
from asyncio import sleep

bot = commands.Bot(command_prefix='>', help_command=None)

cur_day_of_week = ''
cur_time = ''

@bot.command()
async def list(ctx, *args):
    f = open(get_guild_file(ctx.guild))
    data = json.load(f)

    msg = ''
    if len(args) == 0 or args[0] != 'all':
        for noti in data['notifications']:
            if noti['channel_id'] == ctx.channel.id:
                msg += noti['message']
                msg += '\n'
    else:
        for noti in data['notifications']:
            msg += noti['message']
            msg += '\n'
            
    f.close()

    await ctx.send(msg)

@bot.command()
async def help(ctx):
    await ctx.send('no help for you')

# adds notification info to guild json
@bot.command()
async def add(ctx, msg, day, time):
    f = open(get_guild_file(ctx.guild))
    data = json.load(f)
    noti = {
        'message': msg,
        'day_of_week': day,
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

# create guild file when join
@bot.event
async def on_guild_join(guild):
    print('joined', guild)
    f = open(get_guild_file(guild), 'w+')
    default_data = {'notifications': []}
    f.write(json.dumps(default_data, indent=2))
    f.close()

# start tasks 
@bot.event
async def on_ready():
    print('running at', time.ctime(time.time()))
    print('Servers (guilds): ')
    for guild in bot.guilds:
        print(' - ' + guild.name + '  id: ' + str(guild.id))
        f = open(get_guild_file(guild), 'a+')
        # asoejoaej
        f.close()

    await bot.change_presence(status=discord.Status.dnd, activity=discord.Game('>?>>'))
    update_task.before_loop(bot.wait_until_ready)
    update_task.start()


# updates
@tasks.loop(seconds=1)
async def update_task():
    while True:
        if time.localtime().tm_sec == 0:
            await update_cur_time()
            await check_notifications()
            await sleep(55)
        await sleep(0.5)

async def update_cur_time():
    global cur_day_of_week, cur_time
    now = time.localtime()
    cur_day_of_week = str(now.tm_wday)
    cur_time = time.strftime('%H%M', now)

async def check_notifications():
    for guild in bot.guilds:
        f = open(get_guild_file(guild))
        notis = json.load(f)

        for noti in notis['notifications']:
            if noti['day_of_week'] == cur_day_of_week and noti['time'] == cur_time:
                await bot.get_channel(noti['channel_id']).send(noti['message'])
        f.close()

def get_guild_file(guild):
    return 'Guilds/' + guild.name + '_' + str(guild.id) + '.json'

def main():
    # token here just because doesnt matter: OTYxNzU5ODUxODMzMzU2Mjk4.Yk9qqQ.Cp-RSjOzlRByBdj36F0hXRIknTw
    bot.run(env.token)

if __name__ == '__main__':
    main();
