import discord, random, re, tomllib

CONFIG_FILE = "config.toml"

START_TOKEN = "__start"
END_TOKEN = "__end"

config = {
    "client_token": "",
    "max_message_length": 2000,
    "max_message_history": 200,
}

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

        for next_token in re.findall(r"\S+\s*", text):
            self.add_token(last_token, next_token)
            last_token = next_token

        self.add_token(last_token, END_TOKEN)

    def generate_text(self):
        content = ""
        next_token = self.choose_next_token(START_TOKEN)

        while next_token != END_TOKEN and len(content) + len(next_token) <= config["max_message_length"]:
            content += next_token
            next_token = self.choose_next_token(next_token)

        return content

def set_config(options):
    config["client_token"] = options["client_token"]
    config["max_message_history"] = options["max_message_history"]
    config["max_message_length"] = options["max_message_length"]

async def generate_message(channel):
    chain = Chain()

    async for m in channel.history(limit=config["max_message_history"]):
        chain.process_text(m.content)

    return chain.generate_text()

async def send_message(channel):
    async with channel.typing():
        await channel.send(await generate_message(channel))

async def reply_message(message):
    async with message.channel.typing():
        await message.reply(await generate_message(message.channel))

class Mark(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message):
        # Ignore own messages/DMs
        if message.author == self.user or message.guild == None:
            return

        if self.user.mentioned_in(message):
            await reply_message(message)
        elif random.random() < 0.2:
            await send_message(message.channel)

def __main__():
    with open(CONFIG_FILE, "rb") as f:
        set_config(tomllib.load(f))

    intents = discord.Intents.default()
    intents.message_content = True

    client = Mark(intents=intents)
    client.run(config["client_token"])

if __name__ == "__main__":
    __main__()
