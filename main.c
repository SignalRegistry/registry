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

static const char *s_listen_on = "ws://localhost:8000";
static const char *s_web_root = ".";

// This RESTful server implements the following endpoints:
//   /websocket - upgrade to Websocket, and implement websocket echo server
//   /rest - respond with JSON string {"result": 123}
//   any other URI serves static files from s_web_root
static void fn(struct mg_connection *c, int ev, void *ev_data)
{
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
      }
      else if (mg_match(hm->method, mg_str("POST"), NULL))
      {
        MG_INFO(("POST"));  
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

  mg_log_set(MG_LL_DEBUG); 

  mg_mgr_init(&mgr); // Initialise event manager
  printf("Starting WS listener on %s/websocket\n", s_listen_on);
  mg_http_listen(&mgr, s_listen_on, fn, NULL); // Create HTTP listener
  for (;;)
    mg_mgr_poll(&mgr, 1000); // Infinite event loop
  mg_mgr_free(&mgr);
  return 0;
}