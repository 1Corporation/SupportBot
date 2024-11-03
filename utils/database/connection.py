from typing import Optional
import os

import aiosqlite
from dotenv import load_dotenv

from utils import Singleton


load_dotenv()


class DatabaseConnection(Singleton):
    def init(self):
        self.connect: Optional[aiosqlite.Connection] = None

    async def create_tables(self):
        # await self.connect.execute("""CREATE TABLE IF NOT EXISTS messages (
        #     message TEXT PRIMARY KEY
        #     )
        # """)

        # create admin_users table
        await self.connect.execute("""
            CREATE TABLE IF NOT EXISTS helpers (
               user_id INT PRIMARY KEY,
               full_name TEXT 
            )
        """)

        # create tickets table
        await self.connect.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                helper_id INT,
                ticket_author_id INT,
                start_time INT,
                end_time INT,
                FOREIGN KEY (helper_id) REFERENCES helpers(user_id)
            )
        """)

        await self.connect.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                helper_id INT,
                time_at INT,
                FOREIGN KEY (helper_id) REFERENCES helpers(user_id)
            )
        """)

        await self.connect.commit()

    async def get_connection(self):
        self.connect = await aiosqlite.connect(os.getenv("DATABASE_NAME"))
        await self.create_tables()
