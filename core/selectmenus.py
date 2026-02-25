from disnake import ui

class SelectMenu(ui.Select):
    def __init__(self, bot, author_id, options, min_values, max_values, function, *args):
        self.bot = bot
        self.author_id = author_id
        self.function = function
        self.args = args

        super().__init__(
            options=options,
            min_values=min_values,
            max_values=max_values
        )

    async def callback(self, inter):
        if inter.author.id != self.author_id:
            return await inter.send("Bu menüyü kullanamazsın.", ephemeral=True)

        await inter.response.defer(ephemeral=True)
        await self.function(inter, self.values, *self.args)


class SelectMenuDeploy(ui.View):
    def __init__(self, bot, author_id, options, min_values, max_values, function, *args):
        super().__init__(timeout=60)
        self.add_item(
            SelectMenu(bot, author_id, options, min_values, max_values, function, *args)
        )
