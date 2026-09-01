// include/arkhe/ArkheDialect.td
#ifndef ARKHE_DIALECT_TD
#define ARKHE_DIALECT_TD

include "mlir/IR/DialectBase.td"

def ArkheDialect : Dialect {
  let name = "arkhe";
  let summary = "Arkhe OS domain‑specific dialect";
  let description = "Dialeto para plasma, quântica, geometria e consciência.";
  let cppNamespace = "::mlir::arkhe";
}

#endif // ARKHE_DIALECT_TD
