"""
Registry API
"""

from quart import Quart, g, websocket, request, jsonify
import aiosqlite
import sys
import os
import json
import secrets
import argparse

app = Quart(__name__)

app = Quart(__name__)
app.config["DATABASE"] = f"{os.environ.get("HOST")}.db"
app.config["DEBUG"] = True


# ------------------------------------------------------------------------------
# Database Helpers
# ------------------------------------------------------------------------------
async def get_db():
    if "db" not in g:
        g.db = await aiosqlite.connect(f"{os.environ.get("HOST")}.db")
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
    async with aiosqlite.connect(f"{os.environ.get("HOST")}.db") as db:
        await db.execute("PRAGMA journal_mode=WAL;")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                no INTEGER PRIMARY KEY, 
                active INTEGER NOT NULL DEFAULT 1,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                id TEXT UNIQUE NOT NULL, 
                data TEXT NOT NULL
            )
            """
        )
        await db.commit()

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS flows (
                no INTEGER PRIMARY KEY, 
                active INTEGER NOT NULL DEFAULT 1,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                id TEXT UNIQUE NOT NULL, 
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
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
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
        cursor = await db.execute("SELECT id, date, data FROM sources where active = 1")
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("data"), str):
                try:
                    d["data"] = json.loads(d["data"])
                except:
                    pass
            result.append(d)

        return jsonify({"success": 1, "data": result}), 200, common_headers
    elif request.method == "POST":
        body = await request.get_json()
        if not all(k in body for k in ("name", "type")):
            return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        id = secrets.token_hex(3)
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


@app.route("/source/<string:source_id>", methods=["GET", "PUT", "DELETE", "OPTIONS"])
async def source(source_id):
    db = await get_db()
    db.row_factory = aiosqlite.Row
    if request.method == "GET":
        cursor = await db.execute(
            "SELECT id, date, data FROM sources WHERE id = ?", (source_id,)
        )
        rows = [await cursor.fetchone()]

        result = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("data"), str):
                try:
                    d["data"] = json.loads(d["data"])
                except:
                    pass
            result.append(d)
        return jsonify({"success": 1, "data": result}), 200, common_headers
    elif request.method == "PUT":
        body = await request.get_json()
        cursor = await db.execute("SELECT data FROM sources WHERE id = ?", (source_id,))
        row = dict(await cursor.fetchone())
        row["data"] = json.loads(row["data"])
        for key in body.keys():
            row["data"][key] = body[key]
        try:
            cursor = await db.execute(
                "UPDATE sources SET data = ? WHERE id = ?",
                (
                    json.dumps(row["data"], ensure_ascii=False),
                    source_id,
                ),
            )
            await db.commit()

            res_headers = common_headers
            return (
                jsonify({"success": 1, "count": f"{cursor.rowcount}"}),
                200,
                res_headers,
            )
        except Exception as e:
            print(str(e))
            await db.rollback()
            return {"success": 0}, 400, common_headers
    elif request.method == "DELETE":
        try:
            cursor = await db.execute(
                "UPDATE sources SET active = 0 WHERE id = ?", (source_id,)
            )
            await db.commit()

            res_headers = common_headers
            return (
                jsonify({"success": 1, "count": f"{cursor.rowcount}"}),
                200,
                res_headers,
            )
        except Exception as e:
            print(str(e))
            await db.rollback()
            return {"success": 0}, 400, common_headers
    else:
        return (jsonify({"success": 0}), 200, common_headers)


@app.route("/flows", methods=["GET", "POST", "OPTIONS"])
async def flows():
    db = await get_db()
    db.row_factory = aiosqlite.Row
    if request.method == "GET":
        args = request.args.to_dict()

        print(request.args.to_dict())
        if "last_only" in args and args["last_only"] == "1":
            cursor = await db.execute(
                "SELECT id, date, data FROM flows where active = 1"
            )
            rows = [await cursor.fetchone()]
        else:
            cursor = await db.execute("SELECT id, date, data FROM flows")
            rows = await cursor.fetchall()

        result = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("data"), str):
                try:
                    d["data"] = json.loads(d["data"])
                except:
                    pass
            result.append(d)

        return jsonify({"success": 1, "data": result}), 200, common_headers
    elif request.method == "POST":
        body = await request.get_json()
        # if not all(k in body for k in ("name", "type")):
        #     return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        id = secrets.token_hex(3)
        try:
            cursor = await db.execute("UPDATE flows SET active = 0")
            await db.commit()

            await db.execute(
                "INSERT INTO flows(id, data) VALUES(?,?)",
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

    app.run(port=int(os.environ["PORT"]), debug=True)
    # Your app logic goes here
    # print("Hello, World.")


if __name__ == "__main__":
    DATA_FOLDER = os.environ.get("DATA_FOLDER")
    if not DATA_FOLDER:
        raise RuntimeError("'DATA_FOLDER' must be set as environment variable.")
    parser = argparse.ArgumentParser(
        prog="registry-api", description="Registry API for storing sources and flows"
    )
    parser.add_argument("--host", help="hostname for database", type=str, nargs=1, required=True)
    parser.add_argument("--port", help="listening port", type=str, nargs=1, required=True)
    try:
        args = parser.parse_args(sys.argv[1:])
    except Exception as e:
        print(parser.format_help())
        print(str(e))
        exit()
    os.environ["HOST"] = args.host[0]
    os.environ["PORT"] = args.port[0]
    main()
