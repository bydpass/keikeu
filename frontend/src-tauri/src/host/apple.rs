use crate::paper::{Error, Result};
use serde_json::Value;
use std::ffi::{CStr, CString};
extern "C" {
    fn keikeu_host_native(input: *const libc::c_char) -> *mut libc::c_char;
}
pub fn call(request: Value) -> Result<Value> {
    let input = CString::new(request.to_string())
        .map_err(|_| Error::new("native_failed", "invalid_native_request"))?;
    let ptr = unsafe { keikeu_host_native(input.as_ptr()) };
    if ptr.is_null() {
        return Err(Error::new("native_failed", "native_operation_failed"));
    }
    let result = serde_json::from_slice(unsafe { CStr::from_ptr(ptr) }.to_bytes());
    unsafe { libc::free(ptr.cast()) };
    result.map_err(|_| Error::new("native_failed", "invalid_native_response"))
}
