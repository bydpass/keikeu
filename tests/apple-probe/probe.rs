use std::ffi::c_int;

extern "C" {
    fn keikeu_apple_roundtrip() -> c_int;
}

/// CP1 verifies the native call boundary without introducing Paper rules.
#[no_mangle]
pub extern "C" fn keikeu_probe() -> c_int {
    unsafe { keikeu_apple_roundtrip() }
}
