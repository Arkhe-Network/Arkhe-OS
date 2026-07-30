//! SuccessRecorder – SQLite-backed persistent recorder for Cathedral ARKHE.
//! Records cognitive rounds, hub performance, and recommendation outcomes.
//! Provides rich analytical queries used by AegisEvolution and dashboards.

use rusqlite::{Connection, params, Result as SqlResult};
use std::path::Path;

#[derive(Debug, Clone)]
pub struct RoundRecord {
    pub round: u32,
    pub acceptance_rate: f32,
    pub memory_proof_used: bool,
    pub timestamp: Option<String>,
}

#[derive(Debug, Clone)]
pub struct HubPerformanceRecord {
    pub hub: String,
    pub round: u32,
    pub acceptance_rate: f32,
    pub volume: u32,
    pub roas: f32,
}

pub struct SuccessRecorder {
    conn: Connection,
}

impl SuccessRecorder {
    /// Creates a new recorder and initializes the schema if it doesn't exist.
    pub fn new(db_path: &str) -> SqlResult<Self> {
        let conn = Connection::open(Path::new(db_path))?;

        // Load schema from external SQL file (recommended)
        let schema = include_str!("success_recorder_schema.sql");
        conn.execute_batch(schema)?;

        Ok(Self { conn })
    }

    // ============================================================
    // RECORDING METHODS
    // ============================================================

    pub fn record_round(
        &mut self,
        round: u32,
        acceptance_rate: f32,
        memory_proof_used: bool,
    ) -> SqlResult<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO rounds (round, acceptance, proof_used)
             VALUES (?1, ?2, ?3)",
            params![round, acceptance_rate, memory_proof_used as i32],
        )?;
        Ok(())
    }

    pub fn record_hub_performance(
        &mut self,
        hub: &str,
        round: u32,
        acceptance_rate: f32,
        volume: u32,
        roas: f32,
    ) -> SqlResult<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO hub_performance
             (hub, round, acceptance_rate, volume, roas)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![hub, round, acceptance_rate, volume, roas],
        )?;
        Ok(())
    }

    pub fn record_recommendation(
        &mut self,
        round: u32,
        hub: &str,
        title: &str,
        url: &str,
        accepted: bool,
    ) -> SqlResult<()> {
        self.conn.execute(
            "INSERT INTO recommendations (round, hub, title, url, accepted)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![round, hub, title, url, accepted as i32],
        )?;
        Ok(())
    }

    // ============================================================
    // ANALYTICAL QUERIES (used by AegisEvolution & dashboards)
    // ============================================================

    /// Returns average acceptance rate over the last N rounds (or all rounds).
    pub fn average_acceptance_rate(&self, last_n: Option<u32>) -> SqlResult<f32> {
        let sql = match last_n {
            Some(n) => format!(
                "SELECT AVG(acceptance) FROM rounds ORDER BY round DESC LIMIT {}",
                n
            ),
            None => "SELECT AVG(acceptance) FROM rounds".to_string(),
        };
        let mut stmt = self.conn.prepare(&sql)?;
        let avg: Option<f32> = stmt.query_row([], |row| row.get(0))?;
        Ok(avg.unwrap_or(0.0))
    }

    /// Returns recent hub performance stats (last N rounds).
    /// Returns: (hub, avg_acceptance_rate, total_volume, avg_roas)
    pub fn recent_hub_stats(&self, last_rounds: u32) -> SqlResult<Vec<(String, f32, u32, f32)>> {
        let mut stmt = self.conn.prepare(
            "SELECT hub, AVG(acceptance_rate), SUM(volume), AVG(roas)
             FROM hub_performance
             WHERE round >= (SELECT MAX(round) - ?1 FROM rounds)
             GROUP BY hub
             ORDER BY AVG(acceptance_rate) DESC"
        )?;
        let rows = stmt.query_map(params![last_rounds], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, f32>(1)?,
                row.get::<_, u32>(2)?,
                row.get::<_, f32>(3)?,
            ))
        })?;
        rows.collect()
    }

    /// Returns acceptance rate for a specific hub over the last N rounds.
    pub fn hub_acceptance_rate(&self, hub: &str, last_n: u32) -> SqlResult<f32> {
        let sql = format!(
            "SELECT AVG(acceptance_rate) FROM hub_performance
             WHERE hub = ?1 ORDER BY round DESC LIMIT {}",
            last_n
        );
        let mut stmt = self.conn.prepare(&sql)?;
        let avg: Option<f32> = stmt.query_row(params![hub], |row| row.get(0))?;
        Ok(avg.unwrap_or(0.0))
    }

    /// Returns the percentage of rounds where a memory proof was used.
    pub fn memory_proof_usage_rate(&self, last_n: Option<u32>) -> SqlResult<f32> {
        let sql = match last_n {
            Some(n) => format!(
                "SELECT AVG(proof_used) FROM rounds ORDER BY round DESC LIMIT {}",
                n
            ),
            None => "SELECT AVG(proof_used) FROM rounds".to_string(),
        };
        let mut stmt = self.conn.prepare(&sql)?;
        let rate: Option<f32> = stmt.query_row([], |row| row.get(0))?;
        Ok(rate.unwrap_or(0.0))
    }

    /// Returns total recommendation volume per hub in recent rounds.
    pub fn recommendation_volume_by_hub(&self, last_rounds: u32) -> SqlResult<Vec<(String, u32)>> {
        let mut stmt = self.conn.prepare(
            "SELECT hub, COUNT(*) FROM recommendations
             WHERE round >= (SELECT MAX(round) - ?1 FROM rounds)
             GROUP BY hub ORDER BY COUNT(*) DESC"
        )?;
        let rows = stmt.query_map(params![last_rounds], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, u32>(1)?))
        })?;
        rows.collect()
    }

    /// Returns acceptance ratio (accepted / total) per hub in recent rounds.
    pub fn hub_acceptance_ratio(&self, last_rounds: u32) -> SqlResult<Vec<(String, f32)>> {
        let mut stmt = self.conn.prepare(
            "SELECT hub, AVG(accepted) FROM recommendations
             WHERE round >= (SELECT MAX(round) - ?1 FROM rounds)
             GROUP BY hub ORDER BY AVG(accepted) DESC"
        )?;
        let rows = stmt.query_map(params![last_rounds], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, f32>(1)?))
        })?;
        rows.collect()
    }

    /// Returns the top performing hubs (by acceptance rate) with minimum round count.
    pub fn get_top_performing_hubs(&self, min_rounds: u32) -> SqlResult<Vec<(String, f32, u32)>> {
        let mut stmt = self.conn.prepare(
            "SELECT hub, AVG(acceptance_rate), COUNT(*)
             FROM hub_performance
             GROUP BY hub
             HAVING COUNT(*) >= ?1
             ORDER BY AVG(acceptance_rate) DESC"
        )?;
        let rows = stmt.query_map(params![min_rounds], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, f32>(1)?,
                row.get::<_, u32>(2)?,
            ))
        })?;
        rows.collect()
    }

    /// Returns the most recent N rounds with their metrics.
    pub fn get_recent_rounds(&self, limit: u32) -> SqlResult<Vec<RoundRecord>> {
        let mut stmt = self.conn.prepare(
            "SELECT round, acceptance, proof_used, timestamp
             FROM rounds ORDER BY round DESC LIMIT ?1"
        )?;
        let rows = stmt.query_map(params![limit], |row| {
            Ok(RoundRecord {
                round: row.get(0)?,
                acceptance_rate: row.get(1)?,
                memory_proof_used: row.get::<_, i32>(2)? != 0,
                timestamp: row.get(3)?,
            })
        })?;
        rows.collect()
    }
}
