pub mod verification {
    #[cfg(kani)]
    pub mod kani {
        pub mod substrate {
            include!("../verification/kani/substrate.rs");
        }
        pub mod projection {
            include!("../verification/kani/projection.rs");
        }
    }

    #[cfg(test)]
    pub mod proptest {
        pub mod substrate_prop {
            include!("../verification/proptest/substrate_prop.rs");
        }
    }
}
