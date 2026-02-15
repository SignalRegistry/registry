"""
Registry API
"""


from quart import Quart, websocket

app = Quart(__name__)

@app.route('/')
async def hello():
    return 'hello'


@app.websocket('/ws')
async def ws():
    while True:
        data = await websocket.receive()
        await websocket.send(data)

def main():
    app.run()
    # Your app logic goes here
    # print("Hello, World.")

if __name__ == "__main__":
    main()
