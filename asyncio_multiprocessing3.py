import asyncio
import websockets
import datetime
import logging
from multiprocessing import Process, Queue

import time, datetime, json, os, sys, uuid, pathlib, collections, logging


logging.root.setLevel(0)

class WebSocketServer:
    def __init__(self, host, port, incoming_queue, outgoing_queue):
        self.host = host
        self.port = port
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue
        self.active_connections = set()

    async def receive(self, websocket):
        async for message in websocket:
            start_time = datetime.datetime.now()
            #self.incoming_queue.put(message)

            try:
                self.incoming_queue.put_nowait(message)
            except queue.Full:
                logging.warning("Queue is full, dropping message.")

            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            logging.info(f"Message received at {start_time}, processed in {duration} seconds")

    async def broadcast(self):
        while True:
            if not self.outgoing_queue.empty():
                message = self.outgoing_queue.get()
                for websocket in self.active_connections:
                    if not websocket.closed:
                        await websocket.send(message)
            await asyncio.sleep(0.1)  # Avoid busy waiting

    async def handler(self, websocket, path):
        self.active_connections.add(websocket)
        try:
            receiver_task = asyncio.create_task(self.receive(websocket))
            await receiver_task
        finally:
            self.active_connections.remove(websocket)

    async def start_server(self):
        broadcaster_task = asyncio.create_task(self.broadcast())
        server = await websockets.serve(self.handler, self.host, self.port, ssl=None)
        await server.wait_closed()
        broadcaster_task.cancel()

    def run(self):
        asyncio.run(self.start_server())


class MessageHandler:
    def __init__(self, i, incoming_queue, outgoing_queue):
        self.i = i
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue

    def process_incoming_message(self):
        while True:
            if not self.incoming_queue.empty():
                #message = self.incoming_queue.get()

                try:
                    message = self.incoming_queue.get(timeout=1)  # Timeout nach 1 Sekunde
                    self.outgoing_queue.put(message)

                    logging.info(f"Processed message: {message}")

                except queue.Empty:
                    pass # Was zu tun ist, wenn nach dem Timeout nichts in der Queue ist

            time.sleep(0.1)


def main():
    incoming_queue = Queue()
    outgoing_queue = Queue()

    host = '0.0.0.0'
    port = 8765

    ws_server = WebSocketServer(host, port, incoming_queue, outgoing_queue)
    message_handler = MessageHandler(0.1, incoming_queue, outgoing_queue)

    p1 = Process(target=ws_server.run)
    p2 = Process(target=message_handler.process_incoming_message)

    p1.start()
    p2.start()

    p1.join()
    p2.join()


if __name__ == "__main__":
    main()
