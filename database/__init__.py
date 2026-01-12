import aiosqlite

#Scary
class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    # This is mostly for the .reboot command
    async def set_reboot_channel(self, channel_id: int) -> None:
        await self.connection.execute(
            'DELETE FROM default_channel'  # I doubt I need this part
        )
        await self.connection.execute(
            'INSERT INTO default_channel (channel_id) VALUES (?)',
            (channel_id,)
        )
        await self.connection.commit()

    # Bot uses this on boot I think
    async def get_reboot_channel(self) -> int | None:
        rows = await self.connection.execute(
            'SELECT channel_id FROM default_channel LIMIT 1'
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None
        
    # Bot uses this on boot asw
    async def clear_reboot_channel(self) -> None:
        await self.connection.execute('DELETE FROM default_channel')
        await self.connection.commit()


    #Potatoooo
    async def add_potato(self, user_id: int) -> None:
        await self.connection.execute(
            "INSERT OR IGNORE INTO potatoes (user_id) VALUES (?)",
            (user_id,)
        )
        await self.connection.commit()

    async def remove_potato(self, user_id: int) -> None:
        await self.connection.execute(
            "DELETE FROM potatoes WHERE user_id = ?",
            (user_id,)
        )
        await self.connection.commit()

    async def is_potato(self, user_id: int) -> bool:
        rows = await self.connection.execute(
            "SELECT user_id FROM potatoes WHERE user_id = ?",
            (user_id,)
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result is not None

    async def get_all_potatoes(self) -> list:
        rows = await self.connection.execute("SELECT user_id FROM potatoes")
        async with rows as cursor:
            results = await cursor.fetchall()
            return [row[0] for row in results]