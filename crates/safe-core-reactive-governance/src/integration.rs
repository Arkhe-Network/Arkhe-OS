use crate::ReactiveLog;
use async_trait::async_trait;

#[async_trait]
pub trait UedGovernance {
    async fn is_frozen(&self) -> bool;
    async fn get_reward_adjustment(&self, teacher_id: &str) -> f64;
    async fn get_rollback_sth(&self) -> Option<Vec<u8>>;
}

#[async_trait]
pub trait SparseRouterGovernance {
    async fn is_route_banned(&self, router_id: &str, from_module: &str, to_module: &str) -> bool;
    async fn is_frozen(&self) -> bool;
}

#[async_trait]
impl UedGovernance for ReactiveLog {
    async fn is_frozen(&self) -> bool {
        self.is_frozen().await
    }

    async fn get_reward_adjustment(&self, teacher_id: &str) -> f64 {
        self.get_teacher_reward_delta(teacher_id).await
    }

    async fn get_rollback_sth(&self) -> Option<Vec<u8>> {
        self.get_last_rollback_sth().await
    }
}

#[async_trait]
impl SparseRouterGovernance for ReactiveLog {
    async fn is_route_banned(&self, router_id: &str, from_module: &str, to_module: &str) -> bool {
        self.is_route_banned(router_id, from_module, to_module).await
    }

    async fn is_frozen(&self) -> bool {
        self.is_frozen().await
    }
}
