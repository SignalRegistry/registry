#!/bin/bash

LOG_SECTION () {
  printf '=%.0s' {1..80}; printf '\n'
  echo "[INFO] "$*" ..."
  printf '=%.0s' {1..80}; printf '\n'
}

LOG_SUBSECTION () {
  printf -- '-%.0s' {1..80}; printf '\n'
  echo "[INFO] "$*" ..."
  printf -- '-%.0s' {1..80}; printf '\n'
}

if [ "$1" == "dependencies" ]; then
  LOG_SECTION "Dependencies"
  rm -rf deps
  mkdir deps

  LOG_SUBSECTION "SQLite3 - C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine"
  LIBRARY="sqlite3"
  LIBRARY_OWNER="SQLite"
  LIBRARY_YEAR="2026"
  LIBRARY_VERSION="3510200" # 3.51.2
  LIBRARY_RELEASE_URL="https://sqlite.org/${LIBRARY_YEAR}/sqlite-amalgamation-${LIBRARY_VERSION}.zip"
  echo ${LIBRARY_RELEASE_URL}
  curl -L ${LIBRARY_RELEASE_URL} --output deps/${LIBRARY}.zip
  unzip deps/sqlite3.zip -d deps
  mv deps/sqlite-amalgamation-${LIBRARY_VERSION} deps/sqlite3
  # tar -xf deps/${LIBRARY}.zip --directory deps/ --verbose

  

  LOG_SUBSECTION "Mongoose - Embedded Web Server / Embedded Network Library"
  LIBRARY="mongoose"
  LIBRARY_OWNER="cesanta"
  LIBRARY_VERSION="7.20"
  LIBRARY_RELEASE_URL="https://github.com/${LIBRARY_OWNER}/${LIBRARY}/archive/refs/tags/${LIBRARY_VERSION}.tar.gz"
  curl -L ${LIBRARY_RELEASE_URL} --output deps/${LIBRARY}.tar.gz
  tar -xf deps/${LIBRARY}.tar.gz --directory deps/ --verbose

  # mv "dependencies/argtable-${ARGTABLE_VERSION}/" dependencies/argtable/
  # cd dependencies/argtable
  # cmake -B build -DBUILD_SHARED_LIBS=OFF -DARGTABLE3_ENABLE_TESTS=OFF -DARGTABLE3_ENABLE_EXAMPLES=OFF -DCMAKE_INSTALL_PREFIX="$LOCALAPPDATA"
  # cmake --build build --config Release
  # cmake --install build 
  # cd ../..

fi 

if [ "$1" == "build" ]; then

  echo ===========================================================================
  echo "[INFO] Building ..."
  echo ===========================================================================
  rm -rf build
  cmake -B build -DCMAKE_BUILD_TYPE=Release
  cmake --build build

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