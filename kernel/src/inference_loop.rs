// ============================================================================
// ARKHE Inference Loop — Kernel Module
// ============================================================================

#![no_std]

use core::sync::atomic::{AtomicBool, AtomicU64, Ordering};

pub type BlockCallback = fn(block_data: &[u8], block_number: u64);

#[repr(C)]
pub struct InferenceConfig {
    pub target_fps: u32,
    pub inference_mode: u8,
    pub max_context: u32,
    pub draft_tokens: u8,
    pub tree_width: u8,
    pub block_timeout_ns: u64,
}

impl Default for InferenceConfig {
    fn default() -> Self {
        Self {
            target_fps: 60,
            inference_mode: 2,
            max_context: 65536,
            draft_tokens: 8,
            tree_width: 4,
            block_timeout_ns: 16_666_667,
        }
    }
}

pub struct FpsCounter {
    samples: [u64; 60],
    index: usize,
    total: u64,
    count: usize,
}

impl FpsCounter {
    pub const fn new() -> Self {
        Self {
            samples: [0; 60],
            index: 0,
            total: 0,
            count: 0,
        }
    }

    pub fn record(&mut self, nanos: u64) {
        let old = self.samples[self.index];
        self.samples[self.index] = nanos;
        self.index = (self.index + 1) % 60;
        if self.count < 60 {
            self.total += nanos;
            self.count += 1;
        } else {
            self.total = self.total - old + nanos;
        }
    }

    pub fn average_ns(&self) -> u64 {
        if self.count == 0 { 0 } else { self.total / self.count as u64 }
    }

    pub fn current_fps(&self) -> f64 {
        let avg = self.average_ns() as f64;
        if avg > 0.0 { 1_000_000_000.0 / avg } else { 0.0 }
    }
}

pub struct InferenceLoop {
    config: InferenceConfig,
    running: AtomicBool,
    block_counter: AtomicU64,
    fps_counter: FpsCounter,
    callback: Option<BlockCallback>,
}

#[repr(C)]
#[derive(Debug)]
pub struct InferenceStats {
    pub blocks_generated: u64,
    pub average_ns: u64,
    pub current_fps: f64,
    pub running: bool,
}

impl InferenceLoop {
    pub fn new(target_fps: u32, inference_mode: u8) -> Self {
        Self {
            config: InferenceConfig { target_fps, inference_mode, ..InferenceConfig::default() },
            running: AtomicBool::new(false),
            block_counter: AtomicU64::new(0),
            fps_counter: FpsCounter::new(),
            callback: None,
        }
    }

    pub fn set_block_callback(&mut self, callback: BlockCallback) {
        self.callback = Some(callback);
    }

    pub fn run(&mut self) -> ! {
        self.running.store(true, Ordering::SeqCst);
        let frame_time_ns = 1_000_000_000u64 / self.config.target_fps as u64;

        loop {
            let frame_start = Self::monotonic_ns();
            let block_data: Vec<u8> = Vec::new();
            let block_number = self.block_counter.load(Ordering::SeqCst);

            if let Some(cb) = self.callback {
                cb(&block_data, block_number);
            }

            self.block_counter.fetch_add(1, Ordering::SeqCst);

            let frame_end = Self::monotonic_ns();
            let elapsed = frame_end - frame_start;
            self.fps_counter.record(elapsed);

            if elapsed < frame_time_ns {
                self.sleep_ns(frame_time_ns - elapsed);
            }
        }
    }

    fn monotonic_ns() -> u64 {
        static TIMER: AtomicU64 = AtomicU64::new(0);
        TIMER.fetch_add(16_666_667, Ordering::SeqCst)
    }

    fn sleep_ns(&self, ns: u64) {
        let end = Self::monotonic_ns() + ns;
        while Self::monotonic_ns() < end {
            core::hint::spin_loop();
        }
    }

    pub fn stats(&self) -> InferenceStats {
        InferenceStats {
            blocks_generated: self.block_counter.load(Ordering::SeqCst),
            average_ns: self.fps_counter.average_ns(),
            current_fps: self.fps_counter.current_fps(),
            running: self.running.load(Ordering::SeqCst),
        }
    }
}
