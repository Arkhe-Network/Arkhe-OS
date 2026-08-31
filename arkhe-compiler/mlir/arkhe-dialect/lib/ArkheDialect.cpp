#include "arkhe/ArkheDialect.h"
#include "arkhe/ArkheOps.h"
#include "mlir/IR/Builders.h"
#include "mlir/IR/OpImplementation.h"

using namespace mlir;
using namespace mlir::arkhe;

void ArkheDialect::initialize() {
  addOperations<
#define GET_OP_LIST
#include "arkhe/ArkheOps.cpp.inc"
  >();
}
