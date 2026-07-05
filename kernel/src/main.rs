// ============================================================================
// ARKHE Ω‑TEMP v6.0.0 — KERNEL TEMPORAL (entry point)
// ============================================================================
// O Kernel assume o controle após o bootloader. A lógica vive em `lib.rs`
// (crate `arkhe_kernel`, no_std + alloc). Este arquivo contém apenas o ponto
// de entrada bare-metal, compilado somente para alvos freestanding
// (`target_os = "none"`). Em um alvo hospedado, `main` é trivial — a lógica é
// verificada via a biblioteca.
// ============================================================================

#![cfg_attr(target_os = "none", no_std)]
#![cfg_attr(target_os = "none", no_main)]
#![allow(clippy::empty_loop)]

// ─────────────────────────────────────────────────────────────────────────
// Entrada bare-metal — apenas para alvos freestanding.
// ─────────────────────────────────────────────────────────────────────────
#[cfg(target_os = "none")]
mod bare {
    use core::panic::PanicInfo;
    use core::sync::atomic::{AtomicBool, AtomicU64, Ordering};

    use arkhe_kernel::inference_loop::InferenceLoop;
    use arkhe_kernel::model_loader::ModelLoader;
    use arkhe_kernel::temporal_chain::TemporalHashChain;
    use arkhe_kernel::{orbital_mesh, qart_engine, qip_engine, watchdog};

    static KERNEL_RUNNING: AtomicBool = AtomicBool::new(false);
    static CURRENT_BLOCK: AtomicU64 = AtomicU64::new(0);
    static INFERENCE_COUNT: AtomicU64 = AtomicU64::new(0);

    pub struct SharedMemory {
        pub input_buffer: &'static mut [u8],
        pub output_buffer: &'static mut [u8],
        pub model_state: &'static mut [u8],
        pub chain_buffer: &'static mut [u8],
    }

    static mut SHARED_MEM: Option<SharedMemory> = None;

    #[derive(Clone, Copy, Debug)]
    #[repr(C)]
    pub struct KernelConfig {
        pub total_shards: u32,
        pub block_rate_hz: u32,
        pub inference_mode: u8,
        pub qip_enabled: bool,
        pub qart_enabled: bool,
        pub zk_verification: bool,
        pub bootloader_addr: u64,
    }

    impl Default for KernelConfig {
        fn default() -> Self {
            Self {
                total_shards: 819_200,
                block_rate_hz: 60,
                inference_mode: 2,
                qip_enabled: true,
                qart_enabled: true,
                zk_verification: true,
                bootloader_addr: 0x4000_0000,
            }
        }
    }

    #[repr(C)]
    pub struct BootInfo {
        pub genesis_block_addr: u64,
        pub checkpoint_addr: u64,
        pub shards_detected: u32,
        pub bootloader_sig: [u8; 64],
        pub boot_timestamp: u64,
        pub firmware_version: u32,
    }

    fn is_art_block(data: &[u8]) -> bool {
        data.len() >= 4 && data[0..4] == [b'A', b'R', b'T', 0]
    }

    #[unsafe(no_mangle)]
    pub extern "C" fn kernel_main(bootloader_info: *const BootInfo) -> ! {
        let boot_info = unsafe { &*bootloader_info };

        unsafe {
            SHARED_MEM = Some(SharedMemory {
                input_buffer: core::slice::from_raw_parts_mut(0x5000_0000 as *mut u8, 256 * 1024),
                output_buffer: core::slice::from_raw_parts_mut(0x5004_0000 as *mut u8, 256 * 1024),
                model_state: core::slice::from_raw_parts_mut(
                    0x6000_0000 as *mut u8,
                    256 * 1024 * 1024,
                ),
                chain_buffer: core::slice::from_raw_parts_mut(0x7000_0000 as *mut u8, 1024 * 1024),
            });
        }

        let config = KernelConfig::default();
        let mut chain = TemporalHashChain::new(config.total_shards);
        chain.import_genesis(boot_info.genesis_block_addr);

        watchdog::init(core::time::Duration::from_secs(30));
        KERNEL_RUNNING.store(true, Ordering::SeqCst);

        let mut model_loader = ModelLoader::new();
        model_loader.load_checkpoint(boot_info.checkpoint_addr);

        let mut qip = if config.qip_enabled {
            Some(qip_engine::QIPEngine::new())
        } else {
            None
        };

        let mut qart = if config.qart_enabled {
            Some(qart_engine::QArtEngine::new())
        } else {
            None
        };

        let mut inference = InferenceLoop::new(config.block_rate_hz, config.inference_mode);

        inference.set_block_callback(|block_data, block_number| {
            CURRENT_BLOCK.store(block_number, Ordering::SeqCst);
            INFERENCE_COUNT.fetch_add(1, Ordering::SeqCst);

            let _block_hash = chain.add_block(block_data);

            if let Some(ref mut qip_engine) = qip {
                qip_engine.process_block(block_data, block_number);
            }

            if let Some(ref mut qart_engine) = qart {
                if is_art_block(block_data) {
                    qart_engine.process_art_block(block_data, block_number);
                }
            }

            if block_number % 1000 == 0 {
                chain.verify_integrity();
            }

            watchdog::kick();
        });

        let mut mesh = orbital_mesh::OrbitalMesh::new();
        mesh.start_sync();

        inference.run();
    }

    #[panic_handler]
    fn panic(_info: &PanicInfo) -> ! {
        loop {}
    }
}

// ─────────────────────────────────────────────────────────────────────────
// Alvo hospedado — a lógica é verificada via a biblioteca `arkhe_kernel`.
// ─────────────────────────────────────────────────────────────────────────
#[cfg(not(target_os = "none"))]
fn main() {
    println!(
        "arkhe-kernel: ponto de entrada bare-metal disponível apenas para \
         alvos freestanding (target_os = \"none\"). A lógica está na crate \
         `arkhe_kernel` e é verificável neste alvo."
    );
}
