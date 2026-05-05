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
import logging
from logging.handlers import RotatingFileHandler
import asyncio

app = Quart(__name__)
app.config["DATABASE"] = f"{os.environ.get("HOST")}.db"
app.config["DEBUG"]    = True

ws_clnt = set()

# ------------------------------------------------------------------------------
# Database Helpers
# ------------------------------------------------------------------------------
async def get_db():
    if "db" not in g:
        g.db = await aiosqlite.connect(f"{os.environ.get("DATABASE")}")
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
    async with aiosqlite.connect(f"{os.environ.get("DATABASE")}") as db:
        db.row_factory = aiosqlite.Row
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

        # create source tables
        logging.info("- Creating source tables ...")
        cursor = await db.execute("SELECT id FROM sources;")
        rows = await cursor.fetchall()
        for row in rows:
            source = dict(row)
            logging.info(f"  -- {source['id']}")
            await db.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "source-{source['id']}" (
                    no INTEGER PRIMARY KEY, 
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
    if request.method == "GET":
        cursor = await db.execute("SELECT id, date, data FROM sources where active = 1")
        rows = await cursor.fetchall()

        result = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("data"), str):
                try:
                    d["data"] = json.loads(d["data"])
                except Exception as e:
                    print(str(e))
                    pass
            result.append(d)

        return jsonify({"success": 1, "data": result}), 200, common_headers
    elif request.method == "POST":
        body = await request.get_json()
        if not all(k in body for k in ("name", "type")):
            return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        id = secrets.token_hex(3)
        try:
            await db.execute("INSERT INTO sources(id, data) VALUES(?,?)", (id, json.dumps(body, ensure_ascii="False")),)
            await db.commit()

            await db.execute(f"""
                CREATE TABLE IF NOT EXISTS "source-{id}" (
                    no INTEGER PRIMARY KEY, 
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    id TEXT UNIQUE NOT NULL, 
                    data TEXT NOT NULL
                )
                """
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


@app.route("/source/<string:source_id>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def source(source_id):
    db = await get_db()
    cursor = await db.execute("SELECT id, date, data FROM sources WHERE id = ?", (source_id,))
    row    = await cursor.fetchone()
    if not row:
        return {"success": 0, "message": "SOURCE_NOT_FOUND"}, 404, common_headers
    source = dict(row)
    source["data"] = json.loads(source["data"])
    if request.method == "GET":
        return jsonify({"success": 1, "data": [source]}), 200, common_headers
    elif request.method == "PUT":
        body = await request.get_json()
        row["data"] = json.loads(row["data"])
        for key in body.keys():
            source["data"][key] = body[key]
        try:
            cursor = await db.execute("UPDATE sources SET data = ? WHERE id = ?", (json.dumps(source["data"], ensure_ascii=False), source_id,),)
            await db.commit()
            res_headers = common_headers
            return (jsonify({"success": 1, "count": f"{cursor.rowcount}"}), 200, res_headers,)
        except Exception as e:
            print(str(e))
            await db.rollback()
            return {"success": 0}, 400, common_headers
    elif request.method == "POST":
        body = await request.get_json() 
        if not all(k in body for k in ("data",)):
            return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        if not all(k in body["data"] for k in ("value",)):
            return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        data_id = secrets.token_hex(3)
        try:
            await db.execute(f'INSERT INTO "source-{source_id}"(id, data) VALUES(?,?)', (data_id, json.dumps(body, ensure_ascii="False")),)
            await db.commit()
            
            res_headers = common_headers
            res_headers["Location"] = f"{request.base_url}/source/{source_id}/{data_id}"
            await broadcast(json.dumps({"type": "event", "event": "SOURCE_DATA_INSERT", "source_id": f"{source_id}", "data_id": f"{data_id}", "data": body["data"]}, ensure_ascii=False))
            return (jsonify({"success": 1, "id": f"{data_id}"}), 201, res_headers)
        except Exception as e:
            logging.error(f"  -- {str(e)}")
            await db.rollback()
            return {"success": 0}, 400, common_headers
    elif request.method == "DELETE":
        try:
            cursor = await db.execute("UPDATE sources SET active = 0 WHERE id = ?", (source_id,))
            await db.commit()
            res_headers = common_headers
            return (jsonify({"success": 1, "count": f"{cursor.rowcount}"}), 200, res_headers,)
        except Exception as e:
            print(str(e))
            await db.rollback()
            return {"success": 0}, 400, common_headers
    else:
        return (jsonify({"success": 0}), 200, common_headers)
    
@app.route("/source/<string:source_id>/data", methods=["GET", "OPTIONS"])
async def source_data(source_id):
    db = await get_db()
    cursor = await db.execute(f'SELECT id, date, data FROM "source-{source_id}";',)
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if isinstance(d.get("data"), str):
            try:
                d["data"] = json.loads(d["data"])
                d["data"] = d["data"]["data"]
            except Exception as e:
                print(str(e))
                pass
        result.append(d)

    return jsonify({"success": 1, "data": result}), 200, common_headers

@app.websocket("/source/<string:source_id>")
async def source_ws(source_id):
    db = await get_db()
    while True:
        body = await websocket.receive() 
        try:
            body = json.loads(body) 
        except json.JSONDecodeError:
            await websocket.send(json.dumps({"success": 0, "message": "INVALID_JSON"}))
            continue
        if not isinstance(body, dict):
            await websocket.send(json.dumps({"success": 0, "message": "INVALID_DATA_TYPE"}))
            continue
        if not all(k in body for k in ("data",)):
            return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        if not all(k in body["data"] for k in ("value",)):
            return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        data_id = secrets.token_hex(3)
        try:
            await db.execute(f'INSERT INTO "source-{source_id}"(id, data) VALUES(?,?)', (data_id, json.dumps(body, ensure_ascii="False")),)
            await db.commit()
            await websocket.send(json.dumps({"success": 1, "id": f"{data_id}"}))
            await broadcast(json.dumps({"type": "event", "event": "SOURCE_DATA_INSERT", "source_id": f"{source_id}", "data_id": f"{data_id}", "data": body["data"]}, ensure_ascii=False))
        except Exception as e:
            logging.error(f"  -- {str(e)}")
            await db.rollback()
            await websocket.send(json.dumps({"success": 0, "id": f"{data_id}"}))


@app.route("/flows", methods=["GET", "POST", "OPTIONS"])
async def flows():
    db = await get_db()
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
                except Exception as e:
                    print(str(e))
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

async def ws_send():
    while True:
        await websocket.send()

async def ws_recv():
    while True:
        data = await websocket.receive()
        print(data)

async def broadcast(message):
    if not ws_clnt: 
        return
    await asyncio.gather(*[client.send(message) for client in ws_clnt], return_exceptions=True)

@app.websocket("/websocket")
async def ws():
    ws_clnt.add(websocket._get_current_object())
    while True:
        data = await websocket.receive()
        await websocket.send(data)

        # send = asyncio.create_task(ws_send())
        # recv = asyncio.create_task(ws_recv())
        # await asyncio.gather(send, recv)


def main():
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
    os.environ["DATABASE"] = os.path.join(DATA_FOLDER, f"{os.environ.get('HOST')}.db")
    os.environ["PORT"] = args.port[0]

    log_hndl_cnsl = logging.StreamHandler(sys.stdout)
    log_hndl_rota = RotatingFileHandler(filename=os.environ.get("DATABASE").replace(".db",".log"), maxBytes=1024*1024, backupCount=3)
    logging.basicConfig(
        encoding='utf-8', format='%(asctime)s %(levelname)s: %(message)s', 
        level=logging.INFO,
        handlers= [log_hndl_cnsl, log_hndl_rota]          
    )
    
    
    app.run(port=int(os.environ["PORT"]), debug=True)
    # Your app logic goes here
    # print("Hello, World.")


if __name__ == "__main__":

    main()
