pub mod phonon;

use thiserror::Error;

#[derive(Error, Debug)]
pub enum HubbleError {
    #[error("Phonon error: {0}")]
    Phonon(String),
}

pub type HubbleResult<T> = Result<T, HubbleError>;
