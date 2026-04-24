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
        
    # hi mr beast im a big fan
    async def add_compromised_account(self, user_id: int, guild_id: int) -> None:
        await self.connection.execute(
            "INSERT OR IGNORE INTO compromised_accounts (user_id, guild_id) VALUES (?, ?)",
            (str(user_id), str(guild_id))
        )
        await self.connection.commit()

    async def get_compromised_guild(self, user_id: int) -> int | None:
        async with self.connection.execute(
            "SELECT guild_id FROM compromised_accounts WHERE user_id = ?",
            (str(user_id),) # not so sure why it needs the ,
        ) as cursor:
            result = await cursor.fetchone()
            return int(result[0]) if result else None
        
    async def remove_compromised_account(self, user_id: int) -> None:
        await self.connection.execute(
            "DELETE FROM compromised_accounts WHERE user_id = ?",
            (str(user_id),)
        )
        await self.connection.commit()

    async def add_scam_hash(self, algo: str, hashthingy: str) -> None:
        await self.connection.execute(
            "INSERT OR IGNORE INTO scam_hashes (algo, hash) VALUES (?, ?)",
            (algo, hashthingy)
        )
        await self.connection.commit()

    async def get_all_scam_hashes(self) -> list[tuple[str, str]]:
        rows = await self.connection.execute("SELECT algo, hash FROM scam_hashes")
        async with rows as cursor:
            results = await cursor.fetchall()
            return [(row[0], row[1]) for row in results]
        
    async def add_training_image(self, filename: str, label: str, phash: str | None, dhash: str | None, ahash: str | None, chash: str | None, confidence: float | None) -> None:
        await self.connection.execute(
            "INSERT OR IGNORE INTO training_images (filename, label, phash, dhash, ahash, chash, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (filename, label, phash, dhash, ahash, chash, confidence)
        )
        await self.connection.commit()

    async def update_training_images_label(self, filenames: list[str], label: str, confirmed_by: str) -> None:
        await self.connection.executemany( # not sure why it needs the executemany thing but it doesn't work otherwise for some reason
            "UPDATE training_images SET label = ?, confirmed_by = ? WHERE filename = ?",
            [(label, confirmed_by, file) for file in filenames]
        )
        await self.connection.commit()

    async def get_expired_pending_images(self, howoldisthis: int) -> list[str]:
        rows = await self.connection.execute(
            "SELECT filename FROM training_images WHERE label = 'pending' AND added_at < datetime('now', ? || ' days')",
            (f"-{howoldisthis}",)
        )
        async with rows as cursor:
            results = await cursor.fetchall()
            return [row[0] for row in results]
        
    async def delete_training_image(self, filename: str) -> None:
        await self.connection.execute(
            "DELETE FROM training_images WHERE filename = ?",
            (filename,) # yet again, no idea why it needs the ,
        )
        await self.connection.commit()
    
    # this is the biggest waste of space ever, thank me later.
    async def add_model_version(self, version: int, accuracy: float, train_n: int, n: int, positives: int, negatives: int, created_by: str) -> None:
        await self.connection.execute(
            "INSERT OR REPLACE INTO model_versions (version, accuracy, train_n, n, positives, negatives, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (version, accuracy, train_n, n, positives, negatives, created_by)
        )
        await self.connection.commit()

    async def get_model_versions(self) -> list[tuple]:
        rows = await self.connection.execute(
            "SELECT version, accuracy, positives, negatives, created_at FROM model_versions ORDER BY version"
        )
        async with rows as cursor:
            return await cursor.fetchall()
        
    async def set_unban_at(self, user_id: int, unban_at) -> None:
        await self.connection.execute(
            "UPDATE compromised_accounts SET unban_at = ? WHERE user_id = ?",
            (unban_at.strftime('%Y-%m-%d %H:%M:%S'), str(user_id))
        )
        await self.connection.commit()
    
    async def get_unban_timehrs(self) -> list[tuple[str, str, str | None]]: # woah
        rows = await self.connection.execute(
            "SELECT user_id, guild_id, dm_message_id FROM compromised_accounts WHERE unban_at IS NOT NULL AND unban_at <= datetime('now')"
        )
        async with rows as cursor:
            return await cursor.fetchall()
        
    async def set_dm_message_id(self, user_id: int, message_id: int) -> None:
        await self.connection.execute(
            "UPDATE compromised_accounts SET dm_message_id = ? WHERE user_id = ?",
            (str(message_id), str(user_id))
        )
        await self.connection.commit()

    # sticky message thingies

    async def set_sticky_message(self, channel_id: int, message: str, set_by: int, last_message_id: int) -> None:
        await self.connection.execute(
            "INSERT INTO sticky_messages (channel_id, message, set_by, last_message_id) VALUES (?, ?, ?, ?) ON CONFLICT(channel_id) DO UPDATE SET message = excluded.message, set_by = excluded.set_by, set_at = CURRENT_TIMESTAMP, last_message_id = excluded.last_message_id",
            (str(channel_id), message, str(set_by), str(last_message_id))
        )
        await self.connection.commit()

    async def get_sticky_message(self, channel_id: int) -> str | None:
        async with self.connection.execute(
            "SELECT message FROM sticky_messages WHERE channel_id = ?",
            (str(channel_id),)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None
        
    async def get_sticky_full(self, channel_id: int) -> tuple | None: # tupletupletuple they're so ueselsasdkfhs
        async with self.connection.execute(
            "SELECT message, set_by, set_at FROM sticky_messages WHERE channel_id = ?",
            (str(channel_id),)
        ) as cursor:
            return await cursor.fetchone()
        
    async def get_sticky_data(self, channel_id: int) -> dict | None: # istg why do I even need like 50 functions to get the same datgjuhdsfgkjd
        async with self.connection.execute(
            "SELECT message, set_by, set_at, last_message_id FROM sticky_messages WHERE channel_id = ?",
            (str(channel_id),)
        ) as cursor:
            result = await cursor.fetchone()
            if not result:
                return None
            return {
                "message": result[0],
                "set_by": result[1],
                "set_at": result[2],
                "last_message_id": int(result[3]) if result[3] else None
            }
        
    async def get_sticky_last_message_id(self, channel_id: int) -> int | None:
        async with self.connection.execute(
            "SELECT last_message_id FROM sticky_messages WHERE channel_id = ?",
            (str(channel_id),)
        ) as cursor:
            result = await cursor.fetchone()
            return int(result[0]) if result and result[0] else None
        
    async def update_sticky_last_message(self, channel_id: int, message_id: int) -> None:
        await self.connection.execute(
            "UPDATE sticky_messages SET last_message_id = ? WHERE channel_id = ?",
            (str(message_id), str(channel_id))
        )
        await self.connection.commit()

    async def remove_sticky_message(self, channel_id: int) -> None:
        await self.connection.execute(
            "DELETE FROM sticky_messages WHERE channel_id = ?",
            (str(channel_id),)
        )
        await self.connection.commit()



# Yes, all of this could be WAY better and WAY faster, but I'm just lazy