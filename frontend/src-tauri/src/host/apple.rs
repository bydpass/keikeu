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

extern "C" {
    fn keikeu_coordinate(
        input: *const libc::c_char,
        context: *mut libc::c_void,
        callback: extern "C" fn(*mut libc::c_void),
    ) -> i32;
}

pub fn coordinate<T, F: FnOnce() -> Result<T>>(request: Value, work: F) -> Result<T> {
    struct Call<F, T> {
        work: Option<F>,
        result: Option<Result<T>>,
    }
    extern "C" fn access<T, F: FnOnce() -> Result<T>>(raw: *mut libc::c_void) {
        let call = unsafe { &mut *raw.cast::<Call<F, T>>() };
        if let Some(work) = call.work.take() {
            call.result = Some(
                std::panic::catch_unwind(std::panic::AssertUnwindSafe(work)).unwrap_or_else(|_| {
                    Err(Error::new("commit_unknown", "native_callback_interrupted"))
                }),
            );
        }
    }
    let input = CString::new(request.to_string())
        .map_err(|_| Error::new("validation_failed", "invalid_coordination_request"))?;
    let mut call = Call {
        work: Some(work),
        result: None,
    };
    let status = unsafe {
        keikeu_coordinate(
            input.as_ptr(),
            (&mut call as *mut Call<F, T>).cast(),
            access::<T, F>,
        )
    };
    if status != 0 {
        return Err(Error::new(
            if call.result.is_some()
                && (request["write"].is_string() || request["initialize"] == true)
            {
                "commit_unknown"
            } else {
                "coordination_failed"
            },
            "native_coordination_incomplete",
        ));
    }
    call.result.unwrap_or_else(|| {
        Err(Error::new(
            "coordination_failed",
            "native_accessor_not_called",
        ))
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn native_batch_encloses_single_rust_accessor() {
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../tests/test-vault")
            .join(format!("coordinate-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(root.join("cache")).unwrap();
        let mut count = 0;
        let value = coordinate(
            serde_json::json!({"root":root,"paths":[],"write":"cache/K-20260907-001.md"}),
            || {
                count += 1;
                std::fs::write(
                    root.join("cache/K-20260907-001.md"),
                    b"synthetic native callback",
                )?;
                Ok(7)
            },
        )
        .unwrap();
        assert_eq!(value, 7);
        assert_eq!(count, 1);
        coordinate(
            serde_json::json!({"root":root,"paths":["cache/K-20260907-001.md"]}),
            || {
                assert_eq!(
                    std::fs::read(root.join("cache/K-20260907-001.md"))?,
                    b"synthetic native callback"
                );
                Ok(())
            },
        )
        .unwrap();
        coordinate(
            serde_json::json!({"root":root,"paths":["cache/missing.md"]}),
            || {
                assert!(!root.join("cache/missing.md").exists());
                Ok(())
            },
        )
        .unwrap();
        assert!(coordinate(
            serde_json::json!({"root":root,"paths":["../escape.md"]}),
            || {
                count += 1;
                Ok(())
            }
        )
        .is_err());
        assert_eq!(count, 1);
    }
}
