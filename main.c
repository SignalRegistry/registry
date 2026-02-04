// #include "mongoose.h"

// // HTTP server event handler function
// void ev_handler(struct mg_connection *c, int ev, void *ev_data) {
//   if (ev == MG_EV_HTTP_MSG) {
//     struct mg_http_message *hm = (struct mg_http_message *) ev_data;
//     struct mg_http_serve_opts opts = { .root_dir = "./web_root/" };
//     mg_http_serve_dir(c, hm, &opts);
//   }
// }

// int main(void) {
//   struct mg_mgr mgr;  // Declare event manager
//   mg_mgr_init(&mgr);  // Initialise event manager
//   mg_http_listen(&mgr, "http://0.0.0.0:8000", ev_handler, NULL);  // Setup listener
//   for (;;) {          // Run an infinite event loop
//     mg_mgr_poll(&mgr, 1000);
//   }
//   return 0;
// }

// Copyright (c) 2020 Cesanta Software Limited
// All rights reserved
//
// Example Websocket server. See https://mongoose.ws/tutorials/websocket-server/

#include "mongoose.h"
#include "sqlite3.h"

static const char *s_listen_on = "ws://localhost:8000";
static const char *s_web_root = ".";

// This RESTful server implements the following endpoints:
//   /websocket - upgrade to Websocket, and implement websocket echo server
//   /rest - respond with JSON string {"result": 123}
//   any other URI serves static files from s_web_root
static void fn(struct mg_connection *c, int ev, void *ev_data)
{
  sqlite3 *db = (struct sqlite3 *)c->mgr->userdata;
  if (ev == MG_EV_HTTP_MSG)
  {
    struct mg_http_message *hm = (struct mg_http_message *)ev_data;

    if (mg_match(hm->uri, mg_str("/websocket"), NULL))
    {
      // Upgrade to websocket. From now on, connection is full-duplex
      // Websocket connection, which will receive MG_EV_WS_MSG events.
      mg_ws_upgrade(c, hm, NULL);
    }
    else if (mg_match(hm->uri, mg_str("/source"), NULL))
    {
      // source operations
      printf("%.*s\n", hm->method.len, hm->method.buf);
      if (mg_match(hm->method, mg_str("GET"), NULL))
      {
        MG_INFO(("GET"));
        printf("%.*s\n", hm->query.len, hm->query.buf);
      }
      else if (mg_match(hm->method, mg_str("POST"), NULL))
      {
        MG_INFO(("POST"));
        printf("%.*s\n", hm->body.len, hm->body.buf);
        struct mg_str key, val;
        size_t ofs = 0;
        while ((ofs = mg_json_next(hm->body, ofs, &key, &val)) > 0)
        {
          printf("%.*s -> %.*s\n", (int)key.len, key.buf, (int)val.len, val.buf);
        }
        char *err_msg = 0;
        char *sql = "INSERT INTO sources(status,type,name,desc) VALUES('active','pulse','Button Press','Button press counter');";
        int rc = sqlite3_exec(db, sql, 0, 0, &err_msg);
        if (rc != SQLITE_OK)
        {
          fprintf(stderr, "3-SQL error: %s\n", err_msg);
          sqlite3_free(err_msg);
          sqlite3_close(db);
          return 1;
        }
      }
      mg_http_reply(c, 200, "", "{\"result\": %d}\n", 123);
    }
    else
    {
      // Serve static files
      struct mg_http_serve_opts opts = {.root_dir = s_web_root};
      mg_http_serve_dir(c, ev_data, &opts);
    }
  }
  else if (ev == MG_EV_WS_MSG)
  {
    // Got websocket frame. Received data is wm->data. Echo it back!
    struct mg_ws_message *wm = (struct mg_ws_message *)ev_data;
    mg_ws_send(c, wm->data.buf, wm->data.len, WEBSOCKET_OP_TEXT);
  }
}

int main(int argc, char *argv[])
{
  struct mg_mgr mgr; // Event manager
  int i;

  sqlite3 *db;
  char *err_msg = 0;

  // Open database
  int rc = sqlite3_open("test.db", &db);
  if (rc != SQLITE_OK)
  {
    fprintf(stderr, "Cannot open database: %s\n", sqlite3_errmsg(db));
    sqlite3_close(db);
    return 1;
  }

  // Create table
  char *sql1 = "DROP TABLE IF EXISTS Sources;"
               "CREATE TABLE Sources(id INTEGER PRIMARY KEY, datetime NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')), status TEXT, type TEXT, name TEXT, desc TEXT);";

  // datetime alternative
  // 'dt1' DATETIME NOT NULL DEFAULT (datetime(CURRENT_TIMESTAMP, 'localtime')),

  rc = sqlite3_exec(db, sql1, 0, 0, &err_msg);
  if (rc != SQLITE_OK)
  {
    fprintf(stderr, "2-SQL error: %s\n", err_msg);
    sqlite3_free(err_msg);
    sqlite3_close(db);
    return 1;
  }

  mg_log_set(MG_LL_DEBUG);

  mg_mgr_init(&mgr); // Initialise event manager
  mgr.userdata = db;
  printf("Starting WS listener on %s/websocket\n", s_listen_on);
  mg_http_listen(&mgr, s_listen_on, fn, NULL); // Create HTTP listener
  for (;;)
    mg_mgr_poll(&mgr, 1000); // Infinite event loop
  mg_mgr_free(&mgr);
  return 0;
}