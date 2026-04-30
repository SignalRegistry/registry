#!/usr/bin/bash

LOG_SECTION () {
  printf '=%.0s' {1..80}; printf '\n'
  echo "$*"
  printf '=%.0s' {1..80}; printf '\n'
}

LOG_SUBSECTION () {
  printf -- '-%.0s' {1..80}; printf '\n'
  echo "$*"
  printf -- '-%.0s' {1..80}; printf '\n'
}

LOG () {
  # LOG_LEVEL="INFO"
  # if [ $# -gt 1 ]; then
  #   LOG_LEVEL=$1
  # else
  #   LOG_LEVEL="INFO"
  # fi
  echo "[$1] "${@:2}""
}

if [[ "$#" -eq 0 || "$1" == "help" ]]; then
    echo "Usage: bash $0 <command>"
    echo ""
    echo "Avaliable commands:"
    echo "    setup      : Display commands in order to setup a similar projects"
    echo "    initialize : Check dependencies and initialize environment"
    echo "    run        : Run development mode"
    echo "    help       : Display this help"
    echo ""
    exit 0
fi

if [[ "$1" == "setup" ]]; then
    LOG_SECTION "Dependencies"
    LOG WARNING "Following coomands will be only listed."
    LOG WARNING "Run if you want to start similar project."
    echo "
uv tool install virtualenv
uv init
mkdir src/${PWD##*/}
cp main.py src/${PWD##*/}/__main__.py
virtualenv .venv
source .venv/bin/activate.sh
uv add briefcase
briefcase convert
"
    exit 0
fi

if [[ "$1" == "initialize" ]]; then
    if [ ! -d ".venv" ] ; then
        LOG INFO "Creating virtual environment ..."
        if ! command -v virtualenv &> /dev/null; then
            LOG INFO "Tool 'virtualenv' not found. Installing ..."
            if ! command -v uv &> /dev/null; then
                LOG INFO "Tool 'uv' not found. Installing ..."
                if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
                    curl -LsSf https://astral.sh/uv/install.sh | sh
                else
                    curl -LsSf https://astral.sh/uv/install.sh | sh
                fi
            fi
            uv tool install virtualenv
        fi
        virtualenv .venv
    fi
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        source .venv/Scripts/activate
    else
        source .venv/bin/activate
    fi
    # exit 0
fi

if [[ "$1" == "run" ]]; then
    uv sync
    briefcase dev --no-isolation
    exit 0
fi

if [ "$1" == "dependencies" ]; then
  LOG_SECTION "Dependencies"
  rm -rf deps
  rm -rf lib
  rm -rf include
  mkdir deps
  mkdir lib
  mkdir include

  LOG_SUBSECTION "Mongoose - Embedded Web Server / Embedded Network Library"
  LIBRARY="mongoose"
  LIBRARY_OWNER="cesanta"
  LIBRARY_VERSION="7.20"
  LIBRARY_RELEASE_URL="https://github.com/${LIBRARY_OWNER}/${LIBRARY}/archive/refs/tags/${LIBRARY_VERSION}.tar.gz"
  LOG INFO Downloading ...
  curl -L ${LIBRARY_RELEASE_URL} --output deps/${LIBRARY}.tar.gz --silent
  LOG INFO Extracting ...
  tar -xf deps/${LIBRARY}.tar.gz --directory deps/
  LOG INFO Building ...
  if [[ "$OSTYPE" == "linux-gnu" ]]; then
    gcc -c -o deps/${LIBRARY}-${LIBRARY_VERSION}/${LIBRARY}.o deps/${LIBRARY}-${LIBRARY_VERSION}/${LIBRARY}.c
    ar rcs -o lib/lib${LIBRARY}.a deps/${LIBRARY}-${LIBRARY_VERSION}/${LIBRARY}.o
  else
    LOG ERROR Unsupported operating system
    exit 1
  fi
  cp deps/${LIBRARY}-${LIBRARY_VERSION}/${LIBRARY}.h include/ 

  LOG_SUBSECTION "SQLite3 - C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine"
  LIBRARY="sqlite3"
  LIBRARY_OWNER="SQLite"
  LIBRARY_YEAR="2026"
  LIBRARY_VERSION="3510200" # 3.51.2
  LIBRARY_RELEASE_URL="https://sqlite.org/${LIBRARY_YEAR}/sqlite-amalgamation-${LIBRARY_VERSION}.zip"
  LOG INFO Downloading ...
  curl -L ${LIBRARY_RELEASE_URL} --output deps/${LIBRARY}.zip --silent
  LOG INFO Extracting ...
  unzip -qq deps/sqlite3.zip -d deps
  mv deps/sqlite-amalgamation-${LIBRARY_VERSION} deps/sqlite3
  LOG INFO Building ...
  if [[ "$OSTYPE" == "linux-gnu" ]]; then
    gcc -c -o deps/${LIBRARY}/${LIBRARY}.o deps/${LIBRARY}/${LIBRARY}.c
    ar rcs -o lib/lib${LIBRARY}.a deps/${LIBRARY}/${LIBRARY}.o
  else
    LOG ERROR Unsupported operating system
    exit 1
  fi
  cp deps/${LIBRARY}/${LIBRARY}.h include/ 

  LOG_SUBSECTION "Jansson - Embedded Web Server / Embedded Network Library"
  LIBRARY="jansson"
  LIBRARY_OWNER="akheron"
  LIBRARY_VERSION="2.15.0"
  LIBRARY_RELEASE_URL="https://github.com/${LIBRARY_OWNER}/${LIBRARY}/releases/download/v${LIBRARY_VERSION}/${LIBRARY}-${LIBRARY_VERSION}.tar.gz"
  LOG INFO Downloading ...
  curl -L ${LIBRARY_RELEASE_URL} --output deps/${LIBRARY}.tar.gz --silent
  LOG INFO Extracting ...
  tar -xf deps/${LIBRARY}.tar.gz --directory deps/ 
  LOG INFO Building ...
  cmake -S deps/${LIBRARY}-${LIBRARY_VERSION} -B deps/${LIBRARY}-${LIBRARY_VERSION}/build -DJANSSON_BUILD_DOCS=OFF -DJANSSON_WITHOUT_TESTS=ON > /dev/null 2>&1
  cmake --build deps/${LIBRARY}-${LIBRARY_VERSION}/build --config Release > /dev/null 2>&1
  cp deps/${LIBRARY}-${LIBRARY_VERSION}/build/include/* include/
  cp deps/${LIBRARY}-${LIBRARY_VERSION}/build/lib/* lib/

fi 

if [ "$1" == "build" ]; then

  echo ===========================================================================
  echo "[INFO] Building ..."
  echo ===========================================================================
  rm -rf build
  cmake -B build -DCMAKE_BUILD_TYPE=Release
  cmake --build build --config Release
fi

if [ "$1" == "install" ]; then

  echo ===========================================================================
  echo "[INFO] Installing ..."
  echo ===========================================================================
  rm -rf build
  cmake -B build -DCMAKE_BUILD_TYPE=Release
  cmake --build build

  if [[ "$OSTYPE" == "linux-gnu" ]]; then
    echo "Here"
  elif [[ "$OSTYPE" == "darwin" ]]; then
          # Mac OSX
    echo "Here"
  elif [[ "$OSTYPE" == "cygwin" ]]; then
          # POSIX compatibility layer and Linux environment emulation for Windows
    echo "Here"
  elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    cmake.exe -B build -DCMAKE_INSTALL_PREFIX="$LOCALAPPDATA"/SignalRegistry  
          # Lightweight shell and GNU utilities compiled for Windows (part of MinGW)
  elif [[ "$OSTYPE" == "win32" ]]; then
          # I'm not sure this can happen.
    echo "Here"
  elif [[ "$OSTYPE" == "freebsd" ]]; then
          # ...
    echo "Here"
  else
          # Unknown.
    echo "Here"
  fi
  cmake --build build --config Release --target INSTALL

fi

if [ "$1" == "publish" ]; then

  echo ===========================================================================
  echo "[INFO] Pıblishing ..."
  echo ===========================================================================
  VERSION=`cat VERSION`
  RELEASE=`git tag -l | tail -1`
  if [ "$RELEASE" = "" ];then
    gh release create "v$VERSION" --generate-notes
  else 
    gh release create "v$VERSION" --generate-notes --notes-start-tag `git tag -l | tail -1`
  fi
  git fetch --tags origin
  # echo $VERSION
  # cd build
  # cpack --config CPackConfig.cmake 
  # cd ..
  # if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  #       # ...
  # elif [[ "$OSTYPE" == "darwin"* ]]; then
  #         # Mac OSX
  # elif [[ "$OSTYPE" == "cygwin" ]]; then
  #         # POSIX compatibility layer and Linux environment emulation for Windows
  # elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
  #         # Lightweight shell and GNU utilities compiled for Windows (part of MinGW)
  # elif [[ "$OSTYPE" == "win32" ]]; then
  #         # I'm not sure this can happen.
  # elif [[ "$OSTYPE" == "freebsd"* ]]; then
  #         # ...
  # else
  #         # Unknown.
  # fi

fi

if [ "$1" == "unpublish" ]; then

  echo ===========================================================================
  echo "[INFO] Remove Publishing ..."
  echo ===========================================================================
  RELEASE=`git tag -l | tail -1`
  gh release delete $RELEASE -y && git push --delete origin $RELEASE && git tag -d $RELEASE 

fi

################################################################################
# Node.js server
################################################################################
# npm i 
# pm2 start main.js --name dash-gui
# pm2 save

################################################################################
# Nginx server block
################################################################################
# rm -f /etc/nginx/sites-enabled/dash.signalregistry.net
# sudo nginx -s reload
# cat > /etc/nginx/sites-enabled/dash.signalregistry.net <<- EOM
# server {

#   listen 443;
#   listen [::]:443;

#   server_name dash.signalregistry.net;

#   add_header Access-Control-Allow-Headers '*';
#   add_header Access-Control-Allow-Methods 'POST, PUT, GET, OPTIONS, DELETE';

#   location / {
#     proxy_pass http://127.0.0.1:9000;
#     proxy_http_version 1.1;
#     proxy_set_header Upgrade \$http_upgrade;
#     proxy_set_header Connection 'upgrade';
#     proxy_set_header Host \$host;
#     proxy_set_header Remote_Uri \$request_uri;
#     proxy_cache_bypass \$http_upgrade;
#   }
# }
# EOM
# sudo nginx -t
# sudo nginx -s reload



