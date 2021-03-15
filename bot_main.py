import discord
import time
import json
from datetime import date, datetime
from discord.enums import Status
from discord.ext import tasks

TOKEN = "BOT_TOKEN" # token for bot
ACCUMULATIVE_DATA_FILE ="acc_data.txt"  # accumulative time holder
DATA_FILE = "data.json" # data file for daily times
OLD_ACC_DATA_FILE = "old_acc_data.json" # data file used to work out daily times
SERVER_ID = 000000000000000000 # copy ID for server it needs to be active in
LOG_CHANNEL_ID = 000000000000000000   # copy ID for a server to log activity
EXCEPTIONS = []    # list of usernames to exclude (add bots etc. here)
BOT_PREFIX = "!"   # prefix for bot commands

bot_pl = len(BOT_PREFIX)

intents = discord.Intents.all()
bot = discord.Client(intents = intents)

guild = None
active_time = None

log_channel = None

server_members = []
online_users = []
calling_users = []

pendingMessages = {}

current_date = date.today()

active = False

@bot.event
async def on_ready():
    global log_channel
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    check_date.start()
    await log(str(bot.user) + " connected.")

@bot.event
async def on_disconnect():
    await log(str(bot.user) + " disconnected.")

@bot.event
async def on_member_update(before, after):
    if active:
        if before.status != Status.offline and after.status == Status.offline:
            await log(before.name + "#" + before.discriminator + " went offline.")
            await went_offline(before.name + "#" + before.discriminator)
        elif before.status == Status.offline and after.status != Status.offline:
            await log(before.name + "#" + before.discriminator + " came online.")
            went_online(before.name + "#" + before.discriminator, time.time())

@tasks.loop(minutes=1.0)
async def check_date():
    global current_date
    if current_date != date.today():
        await save_day()

@tasks.loop(seconds=1.0)
async def update_call(guild):
    if active:
        server_members = guild.members
        for member in server_members:
            found = False
            for user in calling_users:
                if user[0] == member.name + "#" + member.discriminator:
                    found = True
                    if member.voice is None or member.voice.channel is None:
                        await log(user[0] + " left a call.")
                        await left_call(user[0])
            if not found and member.name + "#" + member.discriminator not in EXCEPTIONS and member.voice is not None and member.voice.channel is not None:
                await log(member.name + "#" + member.discriminator + " joined a call.")
                joined_call(member.name + "#" + member.discriminator, time.time())

@bot.event
async def on_message(message):

    if message.author == bot.user or str(message.author) in EXCEPTIONS:
        return

    global active, pendingMessages
    if message.content.startswith(BOT_PREFIX):
        if message.content[bot_pl:] == "start":
            active = True
            if await activate():
                await message.channel.send("Activation Successful")
            else:
                await message.channel.send("Activation Failed")
        elif message.content[bot_pl:] == "stop":
            active = False
            if await deactivate():
                await message.channel.send("Deactivation Successful")
            else:
                await message.channel.send("Deactivation Failed")
        elif message.content[bot_pl:] == "restart":
            if await deactivate():
                if await activate():
                    await message.channel.send("Restart Successful")
                else:
                    await message.channel.send("Restart activation Failed")
            else:
                await message.channel.send("Restart deactivation Failed")
        elif message.content[bot_pl:] == "time" and active:
            await message.channel.send("Time Active: " + read_time(round(time.time() - active_time)))
        elif message.content[bot_pl:] == "time" and not active:
            await message.channel.send("Currently Inactive.")
        elif message.content[bot_pl:].split(" ")[0] == "display":
            if len(message.content[bot_pl:].split(" ", 1)) == 1:
                await message.channel.send(await display_data(str(message.author)))
            else:
                await message.channel.send(await display_data(message.content[bot_pl:].split(" ", 1)[1]))
        elif message.content[bot_pl:] == "file":
            f = open(DATA_FILE, "r")
            await message.channel.send(file=discord.File(f))
            f.close()
        elif message.content[bot_pl:].split(" ")[0] == "today":
            if len(message.content[bot_pl:].split(" ", 1)) == 1:
                await message.channel.send(await display_today(str(message.author)))
            else:
                await message.channel.send(await display_today(message.content[bot_pl:].split(" ", 1)[1]))
    
    elif active:
        await log(str(message.author) + " : " + str(message.content))
        if str(message.author) in pendingMessages:
            pendingMessages[str(message.author)] += 1
        else:
            pendingMessages[str(message.author)] = 1
        await log("Pending messages for " + str(message.author) +": " + str(pendingMessages[str(message.author)]))

async def activate():
    try:
        global active_time
        guild = bot.get_guild(SERVER_ID)
        server_members = guild.members
        for member in server_members:
            if member.status != Status.offline:
                went_online(member.name + "#" + member.discriminator, time.time())
            if member.voice is not None and member.voice.channel is not None:
                joined_call(member.name + "#" + member.discriminator, time.time())
        update_call.start(guild)
        active_time = time.time()
        return True
    except Exception as e:
        await log(e)
        return False


async def deactivate():
    try:
        update_call.stop()
        for member in online_users:
            await went_offline(member[0])
        for member in calling_users:
            await left_call(member[0])
        return True
    except Exception as e:
        await log(e)
        return False  

def read_time(seconds):
    minutes = 0
    hours = 0
    days = 0
    while seconds >= 60:
        seconds -= 60
        minutes += 1
    while minutes >= 60:
        minutes -= 60
        hours += 1
    while hours >= 24:
        hours -= 24
        days += 1
    return str(days) + " days, " + str(hours) + " hours, " + str(minutes) + " minutes, and " + str(seconds) + " seconds."

def went_online(member, time):
    not_online = True
    for user in online_users:
        if user[0] == member:
            not_online = False
    if not_online and member not in EXCEPTIONS:
        online_users.append((member, time))

async def went_offline(member, display = True):
    for i, user in enumerate(online_users):
        if user[0] == member:
            await store_data(user[0], round(time.time() - user[1]), 2, display)
            online_users.pop(i)
            break

def joined_call(member, time):
    not_calling = True
    for user in calling_users:
        if user[0] == member:
            not_calling = False
    if not_calling and member not in EXCEPTIONS:
        calling_users.append((member, time))

async def left_call(member, display = True):
    for i, user in enumerate(calling_users):
        if user[0] == member:
            await store_data(user[0], round(time.time() - user[1]), 1, display)
            calling_users.pop(i)
            break

async def store_data(name, data, index, display = True):
    new_lines = []
    with open(ACCUMULATIVE_DATA_FILE, "r") as f:
        content = f.readlines()

    flag = False
    for item in content:
        item = item.replace("\n","")
        if item[0:item.index("#") + 5] == name:
            flag = True
            old_data = item[item.index("#") + 6:].split(" ")
            old_data[index] = str(int(old_data[index]) + data)
            new_lines.append(name + " " + old_data[0] + " " + old_data[1] + " " + old_data[2])
        else:
            new_lines.append(item)
    
    if not flag:
        new_data = ["0", "0", "0"]
        new_data[index] = str(data)
        new_lines.append(name + " " + new_data[0] + " " + new_data[1] + " " + new_data[2])

    if display:
        await log("Data Updated: " + str(new_lines))

    with open(ACCUMULATIVE_DATA_FILE, "w") as f:
        last_line = new_lines.pop()
        for line in new_lines:
            f.write(line + "\n")
        f.write(last_line)

async def display_data(member):

    global pendingMessages

    with open(ACCUMULATIVE_DATA_FILE, "r") as f:
        content = f.readlines()
    
    flag = False
    data = ["0", "0", "0"]
    for item in content:
        item = item.replace("\n","")
        if item[0:item.index("#") + 5] == member:
            flag = True
            
    if flag:
        online = False
        for user in online_users:
            if user[0] == member:
                online = True

        if online:
            await went_offline(member, False)
            went_online(member, time.time())

        calling = False
        for user in calling_users:
            if user[0] == member:
                calling = True

        if calling:
            await left_call(member, False)
            joined_call(member, time.time())

        if member in pendingMessages:
            await store_data(member, pendingMessages[member], 0, False)
            pendingMessages[member] = 0
        
        with open(ACCUMULATIVE_DATA_FILE, "r") as f:
            content = f.readlines()
        for item in content:
            item = item.replace("\n","")
            if item[0:item.index("#") + 5] == member:
                flag = True
                data = item[item.index("#") + 6:].split(" ")

        return "Data for user " + member + ": \nMessages sent: " + data[0] + "\nTime on call: " + read_time(int(data[1])) + "\nTime online: " + read_time(int(data[2]))
    else:
        return "User not found."

async def display_today(member):

    current_total = None
    try:
        file = open(OLD_ACC_DATA_FILE,"r")
        current_total = json.load(file)
        file.close()
    except:
        current_total = None

    names = []
    data = []

    await display_data(member)

    with open(ACCUMULATIVE_DATA_FILE, "r") as f:
        contents = f.readlines()

    for item in contents:
        item = item.replace("\n", "")
        names.append(item[0:item.index("#") + 5])
        data.append(item[item.index("#") + 6:].split(" "))

    old_names = []
    old_data = []

    if current_total is not None:
        for item in current_total:
            item = item.replace("\n", "")
            old_names.append(item[0:item.index("#") + 5])
            old_data.append(item[item.index("#") + 6:].split(" "))
    else:
        for item in contents:
            item = item.replace("\n", "")
            old_names.append(item[0:item.index("#") + 5])
            old_data.append(["0", "0", "0"])

    for i, name in enumerate(names):
        if name == member:
            return  (
                    "Data for user " + member + " on " + str(current_date) + ": \nMessages sent: " + str(int(data[i][0]) - int(old_data[i][0])) + 
                    "\nTime on call: " + read_time(int(data[i][1]) - int(old_data[i][1])) + 
                    "\nTime online: " + read_time(int(data[i][2]) - int(old_data[i][2]))
                    )

async def log(msg):
    print(msg)
    await log_channel.send(msg)

async def save_day():

    global current_date

    dictionary_data = {}
    try:
        file = open(DATA_FILE,"r")
        dictionary_data = json.load(file)
        file.close()
    except:
        dictionary_data = {}

    current_total = None
    try:
        file = open(OLD_ACC_DATA_FILE,"r")
        current_total = json.load(file)
        file.close()
    except:
        current_total = None

    names = []
    data = []

    with open(ACCUMULATIVE_DATA_FILE, "r") as f:
        contents = f.readlines()

    for item in contents:
        item = item.replace("\n", "")
        await log(await display_data(item[0:item.index("#") + 5]))

    with open(ACCUMULATIVE_DATA_FILE, "r") as f:
        contents = f.readlines()

    for item in contents:
        item = item.replace("\n", "")
        names.append(item[0:item.index("#") + 5])
        data.append(item[item.index("#") + 6:].split(" "))

    old_names = []
    old_data = []

    if current_total is not None:
        for item in current_total:
            item = item.replace("\n", "")
            old_names.append(item[0:item.index("#") + 5])
            old_data.append(item[item.index("#") + 6:].split(" "))
    else:
        for item in contents:
            item = item.replace("\n", "")
            old_names.append(item[0:item.index("#") + 5])
            old_data.append(["0", "0", "0"])

    for i, name in enumerate(names):
        if name in dictionary_data:
            dictionary_data[name][str(current_date)] = [0, 0, 0]
            dictionary_data[name][str(current_date)][0] = int(data[i][0]) - int(old_data[i][0])
            dictionary_data[name][str(current_date)][1] = int(data[i][1]) - int(old_data[i][1])
            dictionary_data[name][str(current_date)][2] = int(data[i][2]) - int(old_data[i][2])
        else:
            dictionary_data[name] = {}
            dictionary_data[name][str(current_date)] = [0, 0, 0]
            dictionary_data[name][str(current_date)][0] = int(data[i][0])
            dictionary_data[name][str(current_date)][1] = int(data[i][1])
            dictionary_data[name][str(current_date)][2] = int(data[i][2])

    await log(dictionary_data)
    file = open(DATA_FILE, "w")
    json.dump(dictionary_data, file)
    file.close()

    file = open(OLD_ACC_DATA_FILE, "w")
    json.dump(contents, file)
    file.close()

    await log(str(current_date) + " saved successfully.")

    current_date = date.today()

bot.run(TOKEN)