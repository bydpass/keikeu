//! Desktop file runtime backed by the shared, GUI-independent Paper rules.
pub(crate) mod store;
pub use keikeu_core::{
    code_sequence, comparison_key, parse, render, validate_code, Error, Page, Paper, Result,
};
pub use store::{Reconcile, Snapshot, Vault};
