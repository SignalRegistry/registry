# Registry API

## Development Platform
- Pardus 25

## Requirements
- Python 3.13

## Initialization (One-Time Setup)
```bash
sudo apt install python3-briefcase      # system-wide briefcase
birefcase new                           # create project
```

## Building
``` bash
python -m venv .venv            # create vitual environment
source ./.venv/bin/activate     # activate virtual environment 
pip install -r requirements.txt # install dependencies
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