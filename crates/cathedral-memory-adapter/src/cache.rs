use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;
use chrono::{Utc, Duration};

struct CacheEntry {
    data: Vec<u8>,
    expires_at: chrono::DateTime<chrono::Utc>,
}

pub struct MemoryCache {
    capacity: usize,
    ttl_seconds: u64,
    cache: Arc<Mutex<HashMap<String, CacheEntry>>>,
}

impl MemoryCache {
    pub fn new(capacity: usize, ttl_seconds: u64) -> Self {
        Self {
            capacity,
            ttl_seconds,
            cache: Arc::new(Mutex::new(HashMap::with_capacity(capacity))),
        }
    }

    pub async fn get(&self, key: &str) -> Option<Vec<u8>> {
        let mut cache = self.cache.lock().await;
        if let Some(entry) = cache.get(key) {
            if Utc::now() < entry.expires_at {
                return Some(entry.data.clone());
            } else {
                cache.remove(key);
            }
        }
        None
    }

    pub async fn set(&self, key: String, data: Vec<u8>) {
        let mut cache = self.cache.lock().await;
        if cache.len() >= self.capacity {
            let mut keys_to_remove = Vec::new();
            let now = Utc::now();
            for (k, v) in cache.iter() {
                if now >= v.expires_at {
                    keys_to_remove.push(k.clone());
                }
            }
            for k in keys_to_remove {
                cache.remove(&k);
            }

            if cache.len() >= self.capacity {
                let first_key = cache.keys().next().cloned().unwrap();
                cache.remove(&first_key);
            }
        }
        let expires_at = Utc::now() + Duration::seconds(self.ttl_seconds as i64);
        cache.insert(key, CacheEntry { data, expires_at });
    }
}
