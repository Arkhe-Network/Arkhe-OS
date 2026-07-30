use safe_core_ethics::{EthicsRule, Severity};
use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};

#[derive(Debug, thiserror::Error)]
pub enum RepositoryError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("Not found: {0}")]
    NotFound(String),
}

pub struct StateRepository {
    pool: SqlitePool,
}

impl StateRepository {
    pub async fn new(database_url: &str) -> Result<Self, RepositoryError> {
        let pool = SqlitePoolOptions::new()
            .connect(if database_url == "sqlite://state.db" { "sqlite::memory:" } else { database_url })
            .await?;

        Self::migrate(&pool).await?;
        Ok(Self { pool })
    }

    async fn migrate(pool: &SqlitePool) -> Result<(), RepositoryError> {
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS ethics_rules (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                constraint_text TEXT NOT NULL,
                severity TEXT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            "#,
        )
        .execute(pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                spec TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_run INTEGER
            )
            "#,
        )
        .execute(pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS metrics_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                metrics_json TEXT NOT NULL
            )
            "#,
        )
        .execute(pool)
        .await?;

        Ok(())
    }

    pub async fn load_all_rules(&self) -> Result<Vec<EthicsRule>, RepositoryError> {
        let rows = sqlx::query_as::<_, (String, String, String, String, bool)>(
            "SELECT id, action, constraint_text, severity, enabled FROM ethics_rules"
        )
        .fetch_all(&self.pool)
        .await?;

        Ok(rows.into_iter().map(|row| {
            let severity = match row.3.as_str() {
                "Block" => Severity::Block,
                "RequireApproval" => Severity::RequireApproval,
                _ => Severity::Allow,
            };

            EthicsRule {
                id: row.0,
                action: row.1,
                constraint: row.2,
                severity,
                enabled: row.4,
            }
        }).collect())
    }

    pub async fn save_rule(&self, rule: &EthicsRule) -> Result<(), RepositoryError> {
        let severity_str = match rule.severity {
            Severity::Block => "Block",
            Severity::RequireApproval => "RequireApproval",
            Severity::Allow => "Allow",
        };

        sqlx::query(
            "INSERT OR REPLACE INTO ethics_rules (id, action, constraint_text, severity, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 0, 0)"
        )
        .bind(&rule.id)
        .bind(&rule.action)
        .bind(&rule.constraint)
        .bind(severity_str)
        .bind(rule.enabled)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    pub async fn save_rules(&self, rules: &[EthicsRule]) -> Result<(), RepositoryError> {
        for rule in rules {
            self.save_rule(rule).await?;
        }
        Ok(())
    }

    pub async fn count_rules(&self) -> Result<i64, RepositoryError> {
        let row: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM ethics_rules").fetch_one(&self.pool).await?;
        Ok(row.0)
    }
}
