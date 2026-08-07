#!/bin/bash

time (
  uvicorn thermo_ui_app:app --port 8080 --no-access-log &
  UVICORN_PID=$!
  while ! curl -s http://127.0.0.1:8080/ > /dev/null; do
    sleep 0.01
  done
  kill $UVICORN_PID
)