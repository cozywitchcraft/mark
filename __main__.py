import collections, discord, random, re, tomllib, time

CONFIG_FILE = "config.toml"

START_TOKEN = "__start"
END_TOKEN = "__end"

SEPARATOR = re.compile(r"\S+\s*")

REPLY_DELAY = 3

channels = {}

class Chain():
    def __init__(self):
        self.tokens = {}

    def add_token(self, last_token, next_token):
        if last_token not in self.tokens:
            self.tokens[last_token] = []

        self.tokens[last_token].append(next_token)

    def choose_next_token(self, last_token):
        return random.choice(self.tokens[last_token])

    def process_text(self, text):
        last_token = START_TOKEN

        for next_token in SEPARATOR.findall(text):
            self.add_token(last_token, next_token)
            last_token = next_token

        if last_token == START_TOKEN:
            return

        self.add_token(last_token, END_TOKEN)

    def generate_text(self, max_length):
        content = ""
        next_token = self.choose_next_token(START_TOKEN)

        while next_token != END_TOKEN and len(content) + len(next_token) <= max_length:
            content += next_token
            next_token = self.choose_next_token(next_token)

        return content

def get_message_content(message):
    return " ".join([message.content, *(attachment.url for attachment in message.attachments)])

class Channel():
    def __init__(self, channel, max_message_history=20000, max_message_length=2000):
        self.channel = channel
        self.max_message_history = max_message_history
        self.max_message_length = max_message_length
        self.messages = collections.deque(maxlen=max_message_history)

    async def read_message_history(self):
        async for message in self.channel.history(limit=self.max_message_history):
            self.messages.append(message)

    def add_message(self, message):
        self.messages.appendleft(message)

    def remove_message(self, message):
        self.messages.remove(message)

    def build_chain(self):
        chain = Chain()

        for message in self.messages:
            chain.process_text(get_message_content(message))

        return chain

    def generate_message(self):
        return self.build_chain().generate_text(self.max_message_length)

async def add_channel(channel):
    # TODO: Channel setting commands
    channels[channel.id] = Channel(channel)
    await channels[channel.id].read_message_history()

def generate_message(channel):
    return channels[channel.id].generate_message()

async def send_message(channel):
    async with channel.typing():
        await channel.send(generate_message(channel))

async def reply_message(message):
    async with message.channel.typing():
        time.sleep(REPLY_DELAY)
        await message.reply(generate_message(message.channel))

class Mark(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message):
        # Ignore own messages/DMs
        if message.author == self.user or message.guild == None:
            return

        if message.channel.id not in channels:
            await add_channel(message.channel)
        else:
            channels[message.channel.id].add_message(message)

        if self.user.mentioned_in(message):
            await reply_message(message)
        elif random.random() < 0.2:
            await send_message(message.channel)

    async def on_message_edit(self, before, after):
        if before.channel.id not in channels or before.content == after.content:
            return

        channels[before.channel.id].remove_message(before)
        channels[before.channel.id].add_message(after)

    async def on_message_delete(self, message):
        if message.channel.id not in channels:
            return

        channels[message.channel.id].remove_message(message)

def __main__():
    with open(CONFIG_FILE, "rb") as f:
        config = tomllib.load(f)

    intents = discord.Intents.default()
    intents.message_content = True

    client = Mark(intents=intents)
    client.run(config["client_token"])

if __name__ == "__main__":
    __main__()
