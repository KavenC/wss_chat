#!/usr/bin/env python

import asyncio
import pathlib
import ssl
import websockets
import logging
import sys
import functools

logging.basicConfig()
logger = logging.getLogger('client')

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.load_verify_locations(
    pathlib.Path(__file__).with_name('server.pem'))


class Prompt:
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.q = asyncio.Queue(loop=self.loop)
        self.loop.add_reader(sys.stdin, self.got_input)

    def got_input(self):
        asyncio.ensure_future(self.q.put(sys.stdin.readline()), loop=self.loop)

    async def __call__(self, msg, end='\n', flush=False):
        print(msg, end=end, flush=flush)
        return (await self.q.get()).rstrip('\n')


prompt = Prompt()
raw_input = functools.partial(prompt, end='', flush=True)


async def start_server(path, port, ssl):
    url = f'wss://{path}:{port}'
    websocket = await websockets.connect(url, ssl=ssl)
    return websocket


async def greet(websocket):
    name = input("What's your name? ")

    await websocket.send(name)
    print(f"> {name}")

    greeting = await websocket.recv()
    print(f"< {greeting}")


async def run(websocket):
    while True:
        try:
            coro1 = asyncio.create_task(input_message(websocket))
            coro2 = asyncio.create_task(print_message(websocket))
            _, pending = await asyncio.wait({coro1, coro2}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
        except KeyboardInterrupt:
            print(' i tihnk i got here?')
            await websocket.close()
            break
    logger.info('bye')


async def input_message(websocket):
    input = await raw_input('>')
    await websocket.send(input)


async def print_message(websocket):
    msg = await websocket.recv()
    print(f'\nreceive message: {msg}')


loop = asyncio.get_event_loop()
tasks = start_server('localhost', '8765', ssl_context)
conn = loop.run_until_complete(tasks)
loop.run_until_complete(greet(conn))
loop.run_until_complete(run(conn))
loop.run_forever()