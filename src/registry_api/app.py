"""
Registry API
"""

from quart import Quart, g, websocket, request, jsonify
import aiosqlite
import sys
import json
from hashlib import blake2b, blake2s

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


common_headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
}


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@app.route("/default", methods=["GET"])
async def default():
    headers = {}
    # for header in request.headers:
    headers = {}
    for key, value in request.headers:
        headers[key] = value
    args = request.args.to_dict()
    data = (await request.get_data()).decode(encoding="utf-8")
    form = await request.form
    body = await request.get_json()
    cookies = request.cookies.to_dict()
    return (
        {
            "success": 1,
            "data": {
                "url": request.url,
                "base_url": request.base_url,
                "headers": headers,
                "args": args,
                "data": data,
                "form": form,
                "body": body,
                "cookies": cookies,
            },
        },
        200,
        common_headers,
    )


@app.route("/sources", methods=["GET", "POST", "OPTIONS"])
async def sources():
    db = await get_db()
    db.row_factory = aiosqlite.Row
    if request.method == "GET":
        cursor = await db.execute("SELECT id, data FROM sources")
        rows = await cursor.fetchall()

        result = [dict(row) for row in rows]  # her satır dict olur
        return jsonify({"success": 1, "data": result}), 200, common_headers
    elif request.method == "POST":
        body = await request.get_json()
        # print(body)
        # return {"success": 1}, 201
        if not all(k in body for k in ("name", "type")):
            return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        if sys.maxsize > 2**32:  # 64bit
            h = blake2b(digest_size=3)
        else:
            h = blake2s(digest_size=3)
        h.update(f"{body["name"]}".encode("utf-8"))
        id = h.hexdigest()
        try:
            await db.execute(
                "INSERT INTO sources(id, data) VALUES(?,?)",
                (id, json.dumps(body, ensure_ascii="False")),
            )
            await db.commit()

            res_headers = common_headers
            res_headers["Location"] = f"{request.base_url}/source/{id}"
            return (jsonify({"success": 1, "id": f"{id}"}), 201, res_headers)
        except Exception:
            await db.rollback()
            return {"success": 0}, 400
    else:
        return {"success": 0}, 400


@app.route("/source", methods=["GET", "POST", "OPTIONS"])
async def source():
    db = await get_db()
    db.row_factory = aiosqlite.Row
    if request.method == "GET":
        cursor = await db.execute("SELECT id, data FROM sources")
        rows = await cursor.fetchall()

        result = [dict(row) for row in rows]  # her satır dict olur
        return jsonify({"success": 1, "data": result}), 200, common_headers
    elif request.method == "POST":
        body = await request.get_json()
        # print(body)
        # return {"success": 1}, 201
        if not all(k in body for k in ("name", "type")):
            return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        if sys.maxsize > 2**32:  # 64bit
            h = blake2b(digest_size=3)
        else:
            h = blake2s(digest_size=3)
        h.update(f"{body["name"]}".encode("utf-8"))
        id = h.hexdigest()
        try:
            await db.execute(
                "INSERT INTO sources(id, data) VALUES(?,?)",
                (id, json.dumps(body, ensure_ascii="False")),
            )
            await db.commit()

            res_headers = common_headers
            res_headers["Location"] = f"{request.base_url}/source/{id}"
            return (jsonify({"success": 1, "id": f"{id}"}), 201, res_headers)
        except Exception:
            await db.rollback()
            return {"success": 0}, 400, common_headers
    else:
        return (jsonify({"success": 0}), 200, common_headers)


@app.websocket("/websocket")
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
