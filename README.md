# Registry API

## Development Platform
- Pardus 25

## Requirements
- Python 3.13

## Initialization (One-Time Setup)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

sudo apt install python3-pdm  # system-wide briefcase
sudo apt install python3-  # system-wide briefcase
pdm init                      # create project
pdm add <package>             # add dependencies  
```

## Building first time
``` bash
virtualenv .venv
source .venv/bin/activate.xsh
uv sync

pdm config python.use_venv true
pdm venv create
pdm use .venv/bin/python
source .venv/bin/activate
pdm install
briefcase convert
```

## Development

Obtain truested certifcates for HTTPS
```bash
sudo apt install mkcert                 # trusted certifier
mkcert -install                         # obtain ssl certificates
mkcert localhost 127.0.0.1 ::1
sudo apt install libnss3-tools          # install for browsers
mkcert -install
```

Run with quart
```bash
cd src/registry_api
quart run --reload --key ../../localhost+2-key.pem --cert ../../localhost+2.pem

```