// scripts/legacy_sunset.rs
//! Identifica código com mais de 5 anos e agenda revisão.

use git2::Repository;
use chrono::{Utc, Duration};

fn main() {
    let repo = Repository::open(".").unwrap();
    let now = Utc::now();
    let cutoff = now - Duration::days(5 * 365); // 5 anos

    for file in repo.index().unwrap().iter() {
        let path = String::from_utf8_lossy(&file.path);
        if !path.ends_with(".rs") { continue; }

        let mut oldest = now;
        let mut revwalk = repo.revwalk().unwrap();
        revwalk.push_head().unwrap();

        for oid in revwalk {
            let commit = repo.find_commit(oid.unwrap()).unwrap();
            if commit.time().seconds() < oldest.timestamp() {
                oldest = chrono::DateTime::from_timestamp(
                    commit.time().seconds(), 0
                ).unwrap();
            }
        }

        if oldest < cutoff {
            eprintln!("⚠️  Legacy code ({}+ years): {}",
                (now - oldest).num_days() / 365, path);
        }
    }
}
