"""
Registry API
"""

from quart import Quart, g, websocket, request
import aiosqlite

app = Quart(__name__)

app = Quart(__name__)
app.config["DATABASE"] = "database.sql"
app.config["DEBUG"] = True


# ------------------------------------------------------------------------------
# Database Helpers
# ------------------------------------------------------------------------------
async def get_db():
    if "db" not in g:
        g.db = await aiosqlite.connect(app.config["DATABASE"])
        g.db.row_factory = aiosqlite.Row

        # WAL mode for better concurrency
        await g.db.execute("PRAGMA journal_mode=WAL;")

    return g.db


@app.teardown_appcontext
async def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        await db.close()


# ------------------------------------------------------------------------------
# Database Initialization
# ------------------------------------------------------------------------------
async def init_db():
    async with aiosqlite.connect(app.config["DATABASE"]) as db:
        await db.execute("PRAGMA journal_mode=WAL;")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                no INTEGER PRIMARY KEY, 
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                id TEXT NOT NULL, 
                data TEXT NOT NULL
            )
            """
        )
        await db.commit()


@app.before_serving
async def startup():
    await init_db()


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@app.route("/sources", methods=["GET", "POST"])
async def sources():
    db = await get_db()
    if request.method == "GET":
        cursor = await db.execute("SELECT id, data FROM sources")
        data = await cursor.fetchall()
        return {"success": 1, "data": data}
    else:
        return {"success": 1, "data": []}


@app.route("/")
async def hello():
    return "hello"


@app.websocket("/ws")
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
