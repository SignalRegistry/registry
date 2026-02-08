cmake_minimum_required(VERSION 3.14)

# -------------------------------------------------
# Project
# -------------------------------------------------
get_filename_component(PROJECT_NAME "${CMAKE_CURRENT_SOURCE_DIR}" NAME)
project(${PROJECT_NAME} LANGUAGES C)

# -------------------------------------------------
# Global options
# -------------------------------------------------
option(BUILD_SHARED_LIBS "Build shared libs" OFF)

# -------------------------------------------------
# Project definitions
# -------------------------------------------------
add_compile_definitions(FUNCTION="${PROJECT_NAME}")

option(ENABLE_TESTS "Build test binaries" ON)

if(UNIX OR MSYS OR MINGW)
  set(CMAKE_INSTALL_PREFIX "/usr/local/SignalRegistry")
elseif(WIN32)
  file(TO_CMAKE_PATH "$ENV{LOCALAPPDATA}" LOCALAPPDATA_CMAKE)
  set(CMAKE_INSTALL_PREFIX "${LOCALAPPDATA_CMAKE}/SignalRegistry")
endif()

message(STATUS "[${PROJECT_NAME}] CMake prefix path: ${CMAKE_INSTALL_PREFIX}")

# -------------------------------------------------
# Version from CHANGELOG
# -------------------------------------------------
file(STRINGS "${CMAKE_SOURCE_DIR}/CHANGELOG.md"
  CHANGELOG_LINES
  REGEX "^## \\[")

list(GET CHANGELOG_LINES 0 FIRST_LINE)

string(REGEX REPLACE "^## \\[(.*)\\].*" "\\1"
  PROJECT_VERSION "${FIRST_LINE}")

string(REGEX REPLACE "^## \\[.*\\] - (.*)" "\\1"
  PROJECT_RELEASE_DATE "${FIRST_LINE}")

message(STATUS "[${PROJECT_NAME}] Version      : ${PROJECT_VERSION}")
message(STATUS "[${PROJECT_NAME}] Release Date : ${PROJECT_RELEASE_DATE}")


set(PROJECT_SOURCES) 
set(PROJECT_LIBRARIES) 
set(PROJECT_INCLUDES) 

# -------------------------------------------------
# Static library (project library)
# -------------------------------------------------
message(STATUS "[${PROJECT_NAME}] ========== Mongoose ========================")
find_library(MONGOOSE_LIBRARY mongoose PATHS "lib/" NO_CACHE NO_DEFAULT_PATH NO_PACKAGE_ROOT_PATH NO_SYSTEM_ENVIRONMENT_PATH)
find_path(MONGOOSE_INCLUDE_PATH mongoose.h PATHS "include/" NO_CACHE NO_DEFAULT_PATH NO_PACKAGE_ROOT_PATH NO_SYSTEM_ENVIRONMENT_PATH)
message(STATUS "[${PROJECT_NAME}] Mongoose include path: ${MONGOOSE_INCLUDE_PATH}")
message(STATUS "[${PROJECT_NAME}] Mongoose library: ${MONGOOSE_LIBRARY}") 
list(APPEND PROJECT_LIBRARIES ${MONGOOSE_LIBRARY})
list(APPEND PROJECT_INCLUDES ${MONGOOSE_INCLUDE_PATH})

message(STATUS "[${PROJECT_NAME}] ========== SQLite3 =========================")
find_library(SQLITE3_LIBRARY sqlite3 PATHS "lib/" NO_CACHE NO_DEFAULT_PATH NO_PACKAGE_ROOT_PATH NO_SYSTEM_ENVIRONMENT_PATH)
find_path(SQLITE3_INCLUDE_PATH sqlite3.h PATHS "include/" NO_CACHE NO_DEFAULT_PATH NO_PACKAGE_ROOT_PATH NO_SYSTEM_ENVIRONMENT_PATH)
message(STATUS "[${PROJECT_NAME}] SQLite3 include path: ${SQLITE3_INCLUDE_PATH}")
message(STATUS "[${PROJECT_NAME}] SQLite3 library: ${SQLITE3_LIBRARY}") 
list(APPEND PROJECT_LIBRARIES ${SQLITE3_LIBRARY})
list(APPEND PROJECT_INCLUDES ${SQLITE3_INCLUDE_PATH})

message(STATUS "[${PROJECT_NAME}] ========== Jansson =========================")
find_library(JANSSON_LIBRARY jansson PATHS "lib/" NO_CACHE NO_DEFAULT_PATH NO_PACKAGE_ROOT_PATH NO_SYSTEM_ENVIRONMENT_PATH)
find_path(JANSSON_INCLUDE_PATH jansson.h PATHS "include/" NO_CACHE NO_DEFAULT_PATH NO_PACKAGE_ROOT_PATH NO_SYSTEM_ENVIRONMENT_PATH)
message(STATUS "[${PROJECT_NAME}] Jansson include path: ${JANSSON_INCLUDE_PATH}")
message(STATUS "[${PROJECT_NAME}] Jansson library: ${JANSSON_LIBRARY}") 
list(APPEND PROJECT_LIBRARIES ${JANSSON_LIBRARY})
list(APPEND PROJECT_INCLUDES ${JANSSON_INCLUDE_PATH})

# -------------------------------------------------
# Sources
# -------------------------------------------------
message(STATUS "[${PROJECT_NAME}] ========== Executable ======================")
list(APPEND PROJECT_SOURCES ${PROJECT_SOURCE_DIR}/main.c)
file(GLOB PROJECT_SOURCES "${PROJECT_SOURCE_DIR}/*.c")
message(STATUS "[${PROJECT_NAME}] List of source files: ${PROJECT_SOURCES}")
message(STATUS "[${PROJECT_NAME}] List of includes: ${PROJECT_INCLUDES}")
message(STATUS "[${PROJECT_NAME}] List of libraries: ${PROJECT_LIBRARIES}")

include_directories(${PROJECT_INCLUDES})
add_executable(${PROJECT_NAME} ${PROJECT_SOURCES})
target_link_libraries(${PROJECT_NAME} ${PROJECT_LIBRARIES})


include(CTest)
enable_testing()

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
