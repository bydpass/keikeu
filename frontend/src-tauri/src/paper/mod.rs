//! Shared Paper v4 rules. No GUI, transport, Index or desktop management.
mod codec;
mod store;
mod unicode_data;
pub use codec::{parse, render, validate_code, Page, Paper};
pub use store::{Reconcile, Snapshot, Vault};

use unicode_normalization::UnicodeNormalization;

pub fn comparison_key(text: &str) -> String {
    let mut out = String::new();
    for c in text.nfc() {
        match unicode_data::CASEFOLD.binary_search_by_key(&c, |(key, _)| *key) {
            Ok(index) => out.push_str(unicode_data::CASEFOLD[index].1),
            Err(_) => out.push(c),
        }
    }
    out
}

use serde::Serialize;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Error {
    pub code: String,
    pub reason: String,
    pub page_number: Option<usize>,
}

pub type Result<T> = std::result::Result<T, Error>;

impl Error {
    pub(crate) fn new(code: &str, reason: &str) -> Self {
        Self {
            code: code.into(),
            reason: reason.into(),
            page_number: None,
        }
    }

    pub(crate) fn format(reason: &str) -> Self {
        Self::new("repair_required", reason)
    }
}

impl From<std::io::Error> for Error {
    fn from(_: std::io::Error) -> Self {
        // Do not echo filesystem paths or author bytes into diagnostics.
        Self::new("operation_failed", "file_operation_failed")
    }
}
