cmake_minimum_required(VERSION 3.20)
project(ArkheDialect)

find_package(MLIR REQUIRED)
find_package(LLVM REQUIRED)

add_definitions(${LLVM_DEFINITIONS})
include_directories(${LLVM_INCLUDE_DIRS})
include_directories(${MLIR_INCLUDE_DIRS})
include_directories(include)

# Dialeto principal
add_mlir_dialect_library(ArkheDialect
    lib/ArkheDialect.cpp
    lib/ArkheOps.cpp
    ADDITIONAL_HEADER_DIRS include/arkhe
    DEPENDS MLIRIR MLIRSupport
    LINK_LIBS PUBLIC MLIRIR
)

# Passes
add_mlir_pass_library(ArkhePasses
    lib/ArkhePasses.cpp
    DEPENDS ArkheDialect
)

# Testes
if(MLIR_ENABLE_TESTS)
    add_mlir_test(arkhe-test test/arkhe-test.mlir)
endif()
