// shaders/causal_order_simulator.wgsl
// ARKHE OS v∞.430.1 — Substrate 91: Variable Causal Order Simulator
// Implements bilateral Fisher-Rao axis with tunable temporal polarization.

struct Uniforms {
    time: f32,                    // Simulation parameter (not "physical time")
    causal_order: f32,            // -1.0: past→future, 0.0: atemporal, +1.0: future→past
    noise_amplitude: f32,         // Quantum fluctuation strength
    rtz_floor: f32,               // Refusal-to-zero threshold (Substrate 85)
    grid_size: u32,               // 1D grid dimension (for 2D: grid_size² cells)
    total_cells: u32,             // grid_size * grid_size
    padding: u32,
};

@group(0) @binding(0) var<uniform> u: Uniforms;
@group(0) @binding(1) var<storage, read_write> coherence_field: array<f32>;
@group(0) @binding(2) var<storage, read_write> phase_field: array<f32>;  // Conjugate field for bilateral dynamics

// Simplex noise for quantum fluctuations (3D variant for spatiotemporal coherence)
fn noise_simplex(x: vec3<f32>) -> f32 {
    // Simplified permutation-based noise; replace with proper simplex for production
    let p = vec3<f32>(127.1, 311.7, 74.3);
    return fract(sin(dot(x, p)) * 43758.5453;
}

@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let idx = id.y * u.grid_size + id.x;
    if (idx >= u.total_cells) { return; }
    
    // Current state
    let phi = coherence_field[idx];      // Coherence amplitude
    let theta = phase_field[idx];         // Conjugate phase (for bilateral dynamics)
    
    // 1. Bilateral neighbor coupling (Fisher-Rao axis without temporal bias)
    // Wrap-around boundary conditions for toroidal topology (Substrate 88)
    let left_idx = (idx + u.grid_size - 1u) % u.total_cells;
    let right_idx = (idx + 1u) % u.total_cells;
    
    let phi_left = coherence_field[left_idx];
    let phi_right = coherence_field[right_idx];
    let theta_left = phase_field[left_idx];
    let theta_right = phase_field[right_idx];
    
    // Symmetric coupling: no inherent directionality
    let phi_neighbor = (phi_left + phi_right) * 0.5;
    let theta_neighbor = (theta_left + theta_right) * 0.5;
    
    // 2. Generalized Langevin dynamics with tunable causal polarization
    // dφ/dt = -∂V/∂φ + ξ(t) + λ·causal_order·(φ - φ_neighbor)
    // where λ controls strength of causal bias
    
    let causal_bias = u.causal_order * 0.1;  // Tunable coupling strength
    let causal_term = causal_bias * (phi - phi_neighbor);
    
    // Quantum fluctuation term (colored noise for spatiotemporal coherence)
    let noise_input = vec3<f32>(
        f32(id.x) / f32(u.grid_size),
        f32(id.y) / f32(u.grid_size),
        u.time * 0.5  // Slower temporal variation for coherence
    );
    let quantum_noise = (noise_simplex(noise_input) - 0.5) * u.noise_amplitude;
    
    // 3. Update coherence field with RTZ Floor (Substrate 85)
    var new_phi = phi + causal_term + quantum_noise;
    new_phi = max(new_phi, u.rtz_floor);  // Refusal to collapse to zero
    
    // 4. Phase evolution: conjugate dynamics for bilateral Fisher-Rao
    // dθ/dt = ω₀ + κ·(θ_neighbor - θ) + noise_phase
    let phase_noise = (noise_simplex(noise_input + vec3<f32>(1.7, 2.3, 0.9)) - 0.5) * u.noise_amplitude * 0.3;
    let phase_coupling = 0.05 * (theta_neighbor - theta);
    var new_theta = theta + phase_coupling + phase_noise;
    
    // Wrap phase to [-π, π]
    new_theta = atan2(sin(new_theta), cos(new_theta));
    
    // 5. Write updated state
    coherence_field[idx] = new_phi;
    phase_field[idx] = new_theta;
}
