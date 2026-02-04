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
file(GLOB MONGOOSE_SOURCES "deps/*/mongoose.c")
file(GLOB MONGOOSE_HEADERS "deps/*/mongoose.h")
set(MONGOOSE_INCLUDE_DIRS "")
foreach(hdr ${MONGOOSE_HEADERS})
get_filename_component(dir ${hdr} DIRECTORY)
list(APPEND MONGOOSE_INCLUDE_DIRS ${dir})
endforeach()
list(REMOVE_DUPLICATES MONGOOSE_INCLUDE_DIRS)
message(STATUS "[${PROJECT_NAME}] List of mongoose source files: ${MONGOOSE_SOURCES}")
message(STATUS "[${PROJECT_NAME}] List of mongoose include files: ${MONGOOSE_HEADERS}")
message(STATUS "[${PROJECT_NAME}] List of mongoose include dirs: ${MONGOOSE_INCLUDE_DIRS}")

add_library(mongoose STATIC ${MONGOOSE_SOURCES})
target_include_directories(mongoose PUBLIC ${MONGOOSE_INCLUDE_DIRS})
get_target_property(MONGOOSE_INCLUDES mongoose INTERFACE_INCLUDE_DIRECTORIES)
list(APPEND PROJECT_INCLUDES ${MONGOOSE_INCLUDES})
list(APPEND PROJECT_LIBRARIES mongoose)
message(STATUS "[${PROJECT_NAME}] List of includes after mongoose: ${PROJECT_INCLUDES}")
message(STATUS "[${PROJECT_NAME}] List of libraries after mongoose: ${PROJECT_LIBRARIES}")

message(STATUS "[${PROJECT_NAME}] ========== SQLite3 =========================")
file(GLOB SQLITE3_SOURCES "deps/*/sqlite3.c")
file(GLOB SQLITE3_HEADERS "deps/*/sqlite3.h")
set(SQLITE3_INCLUDE_DIRS "")
foreach(hdr ${SQLITE3_HEADERS})
get_filename_component(dir ${hdr} DIRECTORY)
list(APPEND SQLITE3_INCLUDE_DIRS ${dir})
endforeach()
list(REMOVE_DUPLICATES SQLITE3_INCLUDE_DIRS)
message(STATUS "[${PROJECT_NAME}] List of sqlite3 source files: ${SQLITE3_SOURCES}")
message(STATUS "[${PROJECT_NAME}] List of sqlite3 include files: ${SQLITE3_HEADERS}")
message(STATUS "[${PROJECT_NAME}] List of sqlite3 include dirs: ${SQLITE3_INCLUDE_DIRS}")

add_library(sqlite3 STATIC ${SQLITE3_SOURCES})
target_include_directories(sqlite3 PUBLIC ${SQLITE3_INCLUDE_DIRS})
# target_compile_definitions(sqlite3 PUBLIC SQLITE_THREADSAFE=1)
get_target_property(SQLITE3_INCLUDES sqlite3 INTERFACE_INCLUDE_DIRECTORIES)
list(APPEND PROJECT_INCLUDES ${SQLITE3_INCLUDES})
list(APPEND PROJECT_LIBRARIES sqlite3)
message(STATUS "[${PROJECT_NAME}] List of includes after sqlite3: ${PROJECT_INCLUDES}")
message(STATUS "[${PROJECT_NAME}] List of libraries after sqlite3: ${PROJECT_LIBRARIES}")


# find_package(SQLite3)
# message(STATUS "[${PROJECT_NAME}] SQLite3 found: ${SQLite3_FOUND}")
# message(STATUS "[${PROJECT_NAME}] SQLite3 version: ${SQLite3_VERSION}")
# message(STATUS "[${PROJECT_NAME}] SQLite3 include directories: ${SQLite3_INCLUDE_DIRS}")
# message(STATUS "[${PROJECT_NAME}] SQLite3 link libraries: ${SQLite3_LIBRARIES}")
# list(APPEND PROJECT_LIBRARIES ${SQLite3_LIBRARIES})
# target_link_libraries(project_target PRIVATE SQLite::SQLite3)

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
