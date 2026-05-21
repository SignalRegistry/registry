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
from python_sqlite_log_handler import SQLiteLogHandler
import asyncio
from jsonschema import validate, ValidationError

app = Quart(__name__)

ws_clnt = set()


# ------------------------------------------------------------------------------
# Database Helpers
# ------------------------------------------------------------------------------
async def get_db():
    if "db" not in g:
        g.db = await aiosqlite.connect(f"{os.environ.get('DATABASE')}")
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
    async with aiosqlite.connect(f"{os.environ.get('DATABASE')}") as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""CREATE TABLE IF NOT EXISTS sources(
            no INTEGER PRIMARY KEY, 
            active INTEGER NOT NULL DEFAULT 1, 
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            id TEXT UNIQUE NOT NULL, 
            data TEXT NOT NULL
            )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS flows(
            no INTEGER PRIMARY KEY, 
            active INTEGER NOT NULL DEFAULT 1, 
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            id TEXT UNIQUE NOT NULL, 
            data TEXT NOT NULL
            )""")
        await db.commit()

        # create source tables
        print("Creating source tables ...")
        app.logger.info("Creating source tables ...")
        cursor = await db.execute("SELECT id FROM sources;")
        rows = await cursor.fetchall()
        for row in rows:
            source = dict(row)
            app.logger.info(f"  -- {source['id']}")
            await db.execute(f"""CREATE TABLE IF NOT EXISTS 'source-{source["id"]}'(
                             no INTEGER PRIMARY KEY, 
                             date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                             id TEXT UNIQUE NOT NULL, 
                             ip TEXT, 
                             location TEXT, 
                             size INTEGER, 
                             value TEXT NOT NULL
                             )""")
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
# Middlewares
# ------------------------------------------------------------------------------
@app.before_request
async def before():
    request.headers["Session-Userid"] = "guest"
    request.headers["Session-Username"] = "guest"
    request.headers["Session-Role"] = "guest"

    real_ip = None or request.headers.get("CF-Connecting-IP")
    real_ip = real_ip or request.headers.get("X-Real-IP")
    real_ip = real_ip or request.headers.get("X-Forwarded-For")

    request.headers["Ip"] = (
        real_ip.split(",")[0].strip() if real_ip else request.remote_addr
    )
    if not request.headers.get("Origin"):
        request.headers["Origin"] = request.headers["Ip"]

    app.logger.info(f"{request.headers['Ip']}")


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
            await db.execute(
                "INSERT INTO sources(id, data) VALUES(?,?)",
                (id, json.dumps(body, ensure_ascii="False")),
            )
            await db.commit()

            await db.execute(f"""
                CREATE TABLE IF NOT EXISTS "source-{id}"(
                no INTEGER PRIMARY KEY, 
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                id TEXT UNIQUE NOT NULL, 
                ip TEXT,
                location TEXT, 
                size INTEGER,
                value TEXT NOT NULL
                )""")
            await db.commit()

            res_headers = common_headers
            res_headers["Location"] = f"{request.base_url}/source/{id}"
            return (jsonify({"success": 1, "id": f"{id}"}), 201, res_headers)
        except Exception:
            await db.rollback()
            return {"success": 0}, 400, common_headers
    else:
        return (jsonify({"success": 0}), 200, common_headers)


@app.route(
    "/source/<string:source_id>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)
async def source(source_id):
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, date, data FROM sources WHERE id = ?", (source_id,)
    )
    row = await cursor.fetchone()
    if not row:
        app.logger.debug(f"{request.headers['Ip']}: {request.path}: 1: SOURCE_NOT_FOUND")
        return ({"success": 0, "message": f"{request.path}: 1: SOURCE_NOT_FOUND"}, 404, common_headers)
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
            cursor = await db.execute(
                "UPDATE sources SET data = ? WHERE id = ?",
                (
                    json.dumps(source["data"], ensure_ascii=False),
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
    elif request.method == "POST":
        body = await request.get_json()
        schema = {
            "type": "object",
            "properties": {"value": {"type": "string"}, "location": {"type": "string"}},
            "required": ["value"],
            "additionalProperties": False,
        }
        if source["data"]["type"] == "Pulse":
            schema["properties"]["value"]["type"] = "number"

        try:
            validate(instance=body, schema=schema)
        except ValidationError as e:
            app.logger.error(f"  -- {str(e)}")
            return {"success": 0, "message": "MISSING_DATA_FIELD"}, 400
        data = body
        data["id"] = secrets.token_hex(3)
        data["ip"] = request.headers["Ip"]
        if "location" not in data:
            data["location"] = "0,0"
        data["size"] = sys.getsizeof(data["value"])
        try:
            sql = (
                f"INSERT INTO 'source-{source_id}'"
                "(id, ip, location, size, value)"
                "VALUES(?,?,?,?,?)"
            )
            await db.execute(
                sql,
                (
                    data["id"],
                    data["ip"],
                    data["location"],
                    data["size"],
                    json.dumps(data["value"], ensure_ascii="False"),
                ),
            )
            await db.commit()

            res_headers = common_headers
            res_headers["Location"] = (
                f"{request.base_url}/source/{source_id}/{data['id']}"
            )
            await broadcast(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "source.data.insert",
                        "params": {
                            "source_id": source_id,
                            "data_id": data["id"],
                        },
                    },
                    ensure_ascii=False,
                )
            )
            return (jsonify({"success": 1, "id": data["id"]}), 201, res_headers)
        except Exception as e:
            app.logger.error(f"  -- {str(e)}")
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


@app.route("/source/<string:source_id>/data", methods=["GET", "OPTIONS"])
async def source_data(source_id):
    db = await get_db()
    cursor = await db.execute(
        f'SELECT id, date, ip, location, size, value FROM "source-{source_id}";',
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["value"] = json.loads(d["value"])
        except Exception as e:
            app.logger.error(str(e))
            pass
        result.append(d)

    return jsonify({"success": 1, "data": result}), 200, common_headers


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
    await asyncio.gather(
        *[client.send(message) for client in ws_clnt], return_exceptions=True
    )


@app.websocket("/rpc")
async def rpc():
    ws_clnt.add(websocket._get_current_object())

    real_ip = None or websocket.headers.get("CF-Connecting-IP")
    real_ip = real_ip or websocket.headers.get("X-Real-IP")
    real_ip = real_ip or websocket.headers.get("X-Forwarded-For")

    websocket.headers["Ip"] = (
        real_ip.split(",")[0].strip() if real_ip else websocket.remote_addr
    )
    if not websocket.headers.get("Origin"):
        websocket.headers["Origin"] = websocket.headers["Ip"]

    app.logger.info(f"{websocket.headers['Ip']} /rpc")

    while True:
        # 1: receive data from sender and parse it as JSON format
        data = await websocket.receive()
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            app.logger.error(f"  -- RPC: 1: JSON_PARSE_ERROR: {str(e)}")
            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 0,
                        "error": {
                            "code": -32602,
                            "message": "RPC: 1:JSON_PARSE_ERROR",
                        },
                    },
                    ensure_ascii=False,
                )
            )
            continue

        # 2: validate base JSON-RPC format
        schema = {
            "type": "object",
            "properties": {
                "jsonrpc": {"type": "string"},
                "method": {"type": "string"},
                "params": {"type": ["array", "object"]},
                "id": {"type": "string"},
            },
            "required": ["jsonrpc", "method"],
            "additionalProperties": True,
        }

        try:
            validate(instance=data, schema=schema)
        except ValidationError as e:
            app.logger.error(f"  -- RPC: 2: JSON_RPC_PARSE_ERROR: {str(e)}")
            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": data.get("id") or "0",
                        "error": {
                            "code": -32602,
                            "message": "RPC: 2: JSON_RPC_PARSE_ERROR",
                        },
                    },
                    ensure_ascii=False,
                )
            )
            continue


        # 3: ping-pong for connection keep-alive
        if data["method"] == "ping":

            # 3.0: validate JSON-RPC format 
            schema = {
                "type": "object",
                "properties": {
                    "jsonrpc": {"type": "string"},
                    "method": {"type": "string"},
                    "params": {"type": ["array", "object"]},
                    "id": {"type": "string"},
                },
                "required": ["jsonrpc", "method", "id"],
                "additionalProperties": False,
            }

            try:
                validate(instance=data, schema=schema)
            except ValidationError as e:
                app.logger.error(f"  -- RPC: 3.0: {data['method']}: JSON_RPC_PARSE_ERROR: {str(e)}")
                await websocket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": data.get("id") or "0",
                            "error": {
                                "code": -32602,
                                "message": "RPC: 3.0: JSON_RPC_PARSE_ERROR",
                            },
                        },
                        ensure_ascii=False,
                    )
                )
                continue 

            await websocket.send(
                 json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": "pong",
                        "id": data["id"]
                    },
                    ensure_ascii=False,
                )
            )
        # 3: data insert to source
        elif data["method"] == "source.data.insert":

            # 3.0: validate JSON-RPC format
            schema = {
                "type": "object",
                "properties": {
                    "jsonrpc": {"type": "string"},
                    "method": {"type": "string"},
                    "params": {"type": ["array", "object"]},
                    "id": {"type": "string"},
                },
                "required": ["jsonrpc", "method", "params", "id"],
                "additionalProperties": False,
            }

            try:
                validate(instance=data, schema=schema)
            except ValidationError as e:
                app.logger.error(f"  -- RPC: 3.0: {data['method']}: JSON_RPC_PARSE_ERROR: {str(e)}")
                await websocket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": data.get("id") or "0",
                            "error": {
                                "code": -32602,
                                "message": "RPC: 3.0: JSON_RPC_PARSE_ERROR",
                            },
                        },
                        ensure_ascii=False,
                    )
                )
                continue

            # 3.1: fetch source info
            if data["params"].get("source_id") is None or not isinstance(
                data["params"]["source_id"], str
            ):
                app.logger.error(f"  -- RPC: 3.1: {data['method']}, {data['id']}: JSON_RPC_PARSE_ERROR: {str(e)}")
                await websocket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": data["id"],
                            "error": {
                                "code": -32602,
                                "message": "RPC: 3.1: MISSING_SOURCE_ID",
                            },
                        },
                        ensure_ascii=False,
                    )
                )
                continue

            db = await get_db()
            cursor = await db.execute(
                "SELECT id, date, data FROM sources WHERE id = ?",
                (data["params"]["source_id"],),
            )
            row = await cursor.fetchone()
            if not row:
                await websocket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": data["id"],
                            "error": {
                                "code": -32602,
                                "message": "SOURCE_NOT_FOUND",
                            },
                        },
                        ensure_ascii=False,
                    )
                )
                continue

            source = dict(row)
            source["data"] = json.loads(source["data"])

            # 3.2: validate data format based on source type
            schema = {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "value": {"type": "any"},
                    "location": {"type": "string"},
                },
                "required": ["source_id", "value"],
                "additionalProperties": False,
            }
            if source["data"]["type"] == "Pulse":
                schema["properties"]["value"] = {"const": 1}
            
            if data.get("params", {}) is None:
                app.logger.error(f"  -- RPC: 3.2: {data['method']}, {data['id']}: JSON_RPC_PARSE_ERROR: {str(e)}")
                await websocket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": data["id"],
                            "error": {
                                "code": -32602,
                                "message": "RPC: 3.2: MISSING_PARAMS",
                            },
                        },
                        ensure_ascii=False,
                    )
                )
                continue

            try:
                validate(instance=data["params"], schema=schema)
            except ValidationError as e:
                app.logger.error(f"  -- RPC: 3.2: {data['method']}, {data['id']}: DATA_VALIDATION_ERROR: {str(e)}")
                await websocket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": data["id"],
                            "error": {
                                "code": -32602,
                                "message": "RPC: 3.2: DATA_VALIDATION_ERROR",
                            },
                        },
                        ensure_ascii=False,
                    )
                )
                continue

            # 3.3: insert data into source table
            data["params"]["id"] = secrets.token_hex(3)
            data["params"]["ip"] = websocket.headers["Ip"]
            if "location" not in data:
                data["params"]["location"] = "0,0"
            data["params"]["size"] = sys.getsizeof(data["params"]["value"])
            try:
                sql = (
                    f"INSERT INTO 'source-{source['data']['id']}'"
                    "(id, ip, location, size, value)"
                    "VALUES(?,?,?,?,?)"
                )
                await db.execute(
                    sql,
                    (
                        data["params"]["id"],
                        data["params"]["ip"],
                        data["params"]["location"],
                        data["params"]["size"],
                        json.dumps(data["params"]["value"], ensure_ascii=False),
                    ),
                )
                await db.commit()
            except Exception as e:
                logging.error(f"  -- RPC: 3.3: {data['method']}, {data['id']}: DATABASE_ERROR: {str(e)}")
                await websocket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": data["id"],
                            "error": {
                                "code": -32603,
                                "message": "RPC: 3.3: DATABASE_ERROR",
                            },
                        },
                        ensure_ascii=False,
                    )
                )
                continue

            # 3.4: respond to sender
            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": data["id"],
                        "result": {
                            "source_id": source["data"]["id"],
                            "data_id": data["params"]["id"],
                        },
                    },
                    ensure_ascii=False,
                )
            )

            # 3.5: broadcast to other clients
            await broadcast(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "source.data.insert",
                        "params": {
                            "source_id": source["data"]["id"],
                            "data_id": data["params"]["id"],
                        },
                    },
                    ensure_ascii=False,
                )
            )


def main():
    DATA_FOLDER = os.environ.get("DATA_FOLDER")
    if not DATA_FOLDER:
        raise RuntimeError("'DATA_FOLDER' must be set as environment variable.")

    parser = argparse.ArgumentParser(
        prog="registry-api", description="Registry API for storing sources and flows"
    )
    parser.add_argument(
        "--host", help="hostname for database", type=str, nargs=1, required=True
    )
    parser.add_argument(
        "--port", help="listening port", type=str, nargs=1, required=True
    )
    try:
        args = parser.parse_args(sys.argv[1:])
    except Exception as e:
        print(parser.format_help())
        print(str(e))
        exit()
    os.environ["HOST"] = args.host[0]
    os.environ["PORT"] = args.port[0]
    os.environ["DATABASE"] = os.path.join(DATA_FOLDER, f"{os.environ.get('HOST')}.db")

    logger = app.logger
    logger.setLevel(logging.DEBUG)

    logger_console = logging.StreamHandler(sys.stdout)
    logger_sqlite = SQLiteLogHandler(db_path=os.environ["DATABASE"], table_name="logs")

    logger_console.setLevel(logging.INFO)
    logger_sqlite.setLevel(logging.DEBUG)

    # logger.addHandler(logger_console)
    logger.addHandler(logger_sqlite)

    app.run(port=int(os.environ["PORT"]), debug=True)


if __name__ == "__main__":
    main()
