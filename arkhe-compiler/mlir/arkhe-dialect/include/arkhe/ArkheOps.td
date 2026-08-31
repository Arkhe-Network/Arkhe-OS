// include/arkhe/ArkheOps.td
#ifndef ARKHE_OPS_TD
#define ARKHE_OPS_TD

include "mlir/IR/OpBase.td"
include "ArkheDialect.td"

def Arkhe_PlasmaInitOp : Op<ArkheDialect, "plasma.init"> {
  let summary = "Inicializa estado de plasma MHD";
  let arguments = (ins TensorOf<[F64]>:$initial_conditions);
  let results = (outs TensorOf<[F64]>:$state);
  let assemblyFormat = "$initial_conditions attr-dict";
}

def Arkhe_PlasmaStepOp : Op<ArkheDialect, "plasma.step"> {
  let summary = "Avança um passo temporal no solver MHD";
  let arguments = (ins TensorOf<[F64]>:$state, F64:$t0, F64:$t1);
  let results = (outs TensorOf<[F64]>:$new_state);
  let assemblyFormat = "$state `,` $t0 `,` $t1 attr-dict";
}

def Arkhe_PlasmaAssertDivFreeOp : Op<ArkheDialect, "plasma.assert_divergence_free"> {
  let summary = "Verifica invariante ∇·B = 0";
  let arguments = (ins TensorOf<[F64]>:$state);
  let assemblyFormat = "$state attr-dict";
}

def Arkhe_GeometryTorusOp : Op<ArkheDialect, "geometry.torus"> {
  let summary = "Constrói um toroide áureo";
  let arguments = (ins F64:$R, F64:$r);
  let results = (outs AnyType:$torus);
  let assemblyFormat = "$R `,` $r attr-dict";
}

def Arkhe_GeometryToGcodeOp : Op<ArkheDialect, "geometry.to_gcode"> {
  let summary = "Converte geometria para G‑code para impressão 3D";
  let arguments = (ins AnyType:$geometry);
  let results = (outs AnyType:$gcode);
  let assemblyFormat = "$geometry attr-dict";
}

#endif // ARKHE_OPS_TD
