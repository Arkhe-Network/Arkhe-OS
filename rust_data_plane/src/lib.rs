// src/lib.rs — Mínimo para compilar e gerar DLL
#[no_mangle]
pub extern "C" fn arkhe_process_cycle(
    _input: *const f32,
    _len: usize,
) -> *mut f32 {
    // Stub: retorna vetor de zeros
    let result = vec![0.0f32; 4]; // action_dim = 4
    let boxed = result.into_boxed_slice();
    let ptr = boxed.as_ptr();
    std::mem::forget(boxed);
    ptr as *mut f32
}

#[no_mangle]
pub extern "C" fn arkhe_free(ptr: *mut f32, len: usize) {
    if !ptr.is_null() {
        unsafe {
            let _ = Vec::from_raw_parts(ptr, len, len);
        }
    }
}
