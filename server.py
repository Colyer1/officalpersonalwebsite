import asyncio
import websockets
import datetime
import json
import aiosqlite
import os

# List to store all connected clients
clients = set()

async def send_messages(websocket, db):
    # Send stored messages to the new client
    async with db.execute('SELECT * FROM messages ORDER BY timestamp') as cursor:
        async for row in cursor:
            await websocket.send(row[1])  # Access the message field by index

async def handle_client(websocket, path, db):
    # Add the new client to the set
    clients.add(websocket)
    try:
        # Send stored messages to the new client
        await send_messages(websocket, db)

        async for message in websocket:
            # Generate a timestamp for the message
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            # Format the message with the timestamp
            formatted_message = f"[{timestamp}] {message}"

            # Save the message to the database
            await db.execute('INSERT INTO messages (timestamp, message) VALUES (?, ?)',
                             (timestamp, formatted_message))
            await db.commit()

            # Broadcast the formatted message to all clients
            await asyncio.gather(
                *[client.send(formatted_message) for client in clients]
            )
    finally:
        # Remove the disconnected client from the set
        clients.remove(websocket)

async def main():
    # Set up the database
    db_filename = 'chat_new.db'  # Change the filename to use a new database
    db_exists = os.path.exists(db_filename)

    db = await aiosqlite.connect(db_filename)
    await db.execute('CREATE TABLE IF NOT EXISTS messages (timestamp TEXT, message TEXT)')
    await db.commit()

    # If the database exists, clear messages on server start
    if db_exists:
        await db.execute('DELETE FROM messages')
        await db.commit()

    async with websockets.serve(lambda ws, path: handle_client(ws, path, db), "localhost", 5555):
        print("Server started.")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
