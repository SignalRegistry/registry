#include <stdlib.h>
#include <stdio.h>
#include <time.h>

#include "mongoose.h"
#include "sqlite3.h"
#include "jansson.h"

#define SOURCE_ID_LEN 6

static const char *s_listen_on = "ws://localhost:8000";
static const char *s_web_root = ".";

// This RESTful server implements the following endpoints:
//   /websocket - upgrade to Websocket, and implement websocket echo server
//   /rest - respond with JSON string {"result": 123}
//   any other URI serves static files from s_web_root
static void fn(struct mg_connection *c, int ev, void *ev_data)
{
  char *sqlite3_err = 0;
  json_error_t *json_err = 0;

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
      if (mg_match(hm->method, mg_str("OPTIONS"), NULL))
      {
        MG_INFO(("OPTIONS"));
        // printf("%.*s\n", hm->query.len, hm->query.buf);
        mg_http_reply(c, 200, "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Headers: *\r\nContent-Type: application/json\r\n", "{\"status\": 0, \"code\": \"SUCCESS\"}\n");
      }
      else if (mg_match(hm->method, mg_str("GET"), NULL))
      {
        MG_INFO(("GET"));
        sqlite3_stmt *stmt;
        int rc;
        const char *sql = "SELECT id, data FROM sources;";
        rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
        if (rc != SQLITE_OK) {
            fprintf(stderr, "Prepare hatası: %s\n", sqlite3_errmsg(db));
            sqlite3_close(db);
            return 1;
        }

        json_t *body = json_loads("{\"status\": 0, \"code\": \"SUCCESS\"}", 0, json_err);
        json_t *data_field = json_array();
        while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
            //int no = sqlite3_column_int(stmt, 0);
            //const unsigned char *datetime = sqlite3_column_text(stmt, 1);
            const unsigned char *id = sqlite3_column_text(stmt, 0);
            const unsigned char *data = sqlite3_column_text(stmt, 1);
            //printf("no        : %d\n", no);
            //printf("datetime  : %s\n", datetime);
            printf("id        : %s\n", id);
            printf("data      : %s\n", data);
            printf("-----------------------------\n");
            json_t *item = json_loads(data, 0, json_err);
            //char *item_str = json_dumps(item, 0);
            //printf("%s\n", item_str);  
            json_object_set_new(item, "id", json_string(id));
            char *item_str = json_dumps(item, 0);
            printf("%s\n", item_str);  
            json_array_append_new(data_field, item);
            char *data_str = json_dumps(data_field, 0);
            printf("%s\n", data_str);  
        }
        json_object_set_new(body, "data", data_field);
        char *body_str = json_dumps(body, 0);
        printf("%s\n", body_str);  
        if (rc != SQLITE_DONE) {
            fprintf(stderr, "Step hatası: %s\n", sqlite3_errmsg(db));
        }
        // printf("%.*s\n", hm->query.len, hm->query.buf);
        mg_http_reply(c, 200, "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Headers: *\r\nContent-Type: application/json\r\n", "%s", body_str);
        free(body_str);
      }
      else if (mg_match(hm->method, mg_str("POST"), NULL))
      {
        MG_INFO(("POST"));
        json_t *body = json_loads(hm->body.buf, 0, json_err);
        json_object_set(body, "status", json_string("active"));
        char id[SOURCE_ID_LEN + 1] = {'\0'};
        srand((int)time(NULL));
        for (int i = 0; i < SOURCE_ID_LEN; i++)
        id[i] = (i % 2 == 0) ? (rand() % 10) + '0' : (char)((int)('a') + rand() % ((int)('z') - (int)('a')));
        id[SOURCE_ID_LEN] = '\0';
        //json_object_set_new(body, "id", json_string(id));
        char *body_str = json_dumps(body, 0);
        json_decref(body);

        char *sql = (char*)malloc((hm->body.len+250) * sizeof(char));

        sprintf(sql, "INSERT INTO sources(id, data) VALUES('%s','%s');", id, body_str);
        printf("%s", sql);
        int rc = sqlite3_exec(db, sql, 0, 0, &sqlite3_err);
        if (rc != SQLITE_OK)
        {
          fprintf(stderr, "3-SQL error: %s\n", sqlite3_err);
          sqlite3_free(sqlite3_err);
          sqlite3_close(db);
          mg_http_reply(c, 200, "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Headers: *\r\nContent-Type: application/json\r\n", "{\"status\": 1, \"code\": \"ERROR_DATABASE_INSERT\"}");
        }
        mg_http_reply(c, 200, "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Headers: *\r\nContent-Type: application/json\r\n", "{\"status\": 0, \"code\": \"SUCCESS\", \"id\": \"%s\"}\n", id);
        free(sql);
        free(body_str);
      }
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
  char *sql1 = "DROP TABLE IF EXISTS Sourcess;"
               "CREATE TABLE IF NOT EXISTS Sources(no INTEGER PRIMARY KEY, datetime NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')), id TEXT NOT NULL, data TEXT);";
  //  "CREATE TABLE Sources(no INTEGER PRIMARY KEY, datetime NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')), status TEXT, type TEXT, name TEXT, desc TEXT);";

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
