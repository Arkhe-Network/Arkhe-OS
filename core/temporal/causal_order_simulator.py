"""
ARKHE OS v∞.430.1 — Substrate 91: Variable Causal Order Simulator
Allows Observer 5D to tune temporal polarization and visualize atemporal coherence fields.
"""
import numpy as np
import wgpu
import pygfx as gfx
from dataclasses import dataclass, field
from typing import Optional, Callable

@dataclass
class CausalOrderConfig:
    """Configuration for causal order simulation."""
    grid_size: int = 256                    # 256×256 coherence field
    causal_order: float = 0.0               # -1.0 to +1.0: temporal polarization
    noise_amplitude: float = 0.08           # Quantum fluctuation strength
    rtz_floor: float = 0.05                 # Refusal-to-zero threshold (Substrate 85)
    time_step: float = 0.01                 # Simulation step (not physical time)
    bilateral_coupling: float = 0.1         # Fisher-Rao coupling strength
    color_map: str = "twilight_shifted"     # Pygfx colormap for visualization

class CausalOrderSimulator:
    """
    Simulates coherence field dynamics with tunable causal order.
    
    Key insight: The field evolution is atemporal; "time" is a parameter
    the Observer uses to traverse the static coherence manifold.
    """
    
    def __init__(self, config: CausalOrderConfig, canvas):
        self.config = config
        self.canvas = canvas
        self.device = wgpu.gpu.request_adapter().request_device()
        
        # Initialize fields
        self.total_cells = config.grid_size ** 2
        self.coherence_field = np.ones(self.total_cells, dtype=np.float32) * 0.5
        self.phase_field = np.zeros(self.total_cells, dtype=np.float32)
        
        # Create GPU buffers
        self._create_buffers()
        self._create_pipeline()
        self._create_visualization()
        
        self.simulation_time = 0.0
        self._on_update: Optional[Callable] = None
        
    def _create_buffers(self):
        """Create GPU storage buffers for coherence and phase fields."""
        # Coherence field buffer
        self.coherence_buffer = self.device.create_buffer(
            size=self.total_cells * 4,  # float32
            usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_DST | wgpu.BufferUsage.COPY_SRC,
        )
        self.coherence_buffer.write_mapped(
            mapping_offset=0,
            data=self.coherence_field.tobytes(),
        )
        
        # Phase field buffer
        self.phase_buffer = self.device.create_buffer(
            size=self.total_cells * 4,
            usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_DST,
        )
        self.phase_buffer.write_mapped(
            mapping_offset=0,
            data=self.phase_field.tobytes(),
        )
        
        # Uniforms buffer
        self.uniforms_buffer = self.device.create_buffer(
            size=48,  # 12 floats for Uniforms struct
            usage=wgpu.BufferUsage.UNIFORM | wgpu.BufferUsage.COPY_DST,
        )
        
    def _create_pipeline(self):
        """Create compute pipeline for causal order dynamics."""
        # Load and compile WGSL shader
        with open("shaders/causal_order_simulator.wgsl", "r") as f:
            shader_code = f.read()
        
        shader_module = self.device.create_shader_module(code=shader_code)
        
        # Pipeline layout and compute pipeline
        # (Simplified; full implementation requires bind group layout definition)
        self.pipeline = self.device.create_compute_pipeline(
            layout="auto",
            compute={"module": shader_module, "entry_point": "main"},
        )
        
    def _create_visualization(self):
        """Create Pygfx scene for coherence field visualization."""
        self.scene = gfx.Scene()
        self.camera = gfx.OrthographicCamera(
            self.config.grid_size, self.config.grid_size, 0, 100
        )
        self.camera.position.z = 50
        
        # Create image texture from coherence field
        self.texture = gfx.Texture(
            data=self.coherence_field.reshape(self.config.grid_size, self.config.grid_size, 1),
            dim=2, size=(self.config.grid_size, self.config.grid_size, 1), format="r8unorm"
        )
        
        # Colormap material for visualization
        self.material = gfx.ImageBasicMaterial(
            map=self.texture,
            color_map=self.config.color_map,
            clim=(0.0, 1.0),
        )
        
        self.image = gfx.Image(
            gfx.Geometry(grid=gfx.Grid(1, 1, self.config.grid_size, self.config.grid_size)),
            self.material,
        )
        self.scene.add(self.image)
        
        self.renderer = gfx.renderers.WgpuRenderer(self.canvas)
        self.controller = gfx.OrbitController(self.camera, register_events=self.renderer)
        
    def update(self, causal_order: Optional[float] = None):
        """
        Update simulation state and render.
        
        Args:
            causal_order: New temporal polarization (-1.0 to +1.0). If None, use current value.
        """
        if causal_order is not None:
            self.config.causal_order = np.clip(causal_order, -1.0, 1.0)
        
        # Update uniforms
        uniforms = np.array([
            self.simulation_time,
            self.config.causal_order,
            self.config.noise_amplitude,
            self.config.rtz_floor,
            self.config.grid_size,
            self.total_cells,
            0, 0, 0, 0, 0  # padding
        ], dtype=np.float32)
        self.uniforms_buffer.write_mapped(0, uniforms.tobytes())
        
        # Dispatch compute shader
        command_encoder = self.device.create_command_encoder()
        compute_pass = command_encoder.begin_compute_pass()
        compute_pass.set_pipeline(self.pipeline)
        # (Bind groups would be set here in full implementation)
        compute_pass.dispatch_workgroups(
            (self.config.grid_size + 15) // 16,
            (self.config.grid_size + 15) // 16,
            1
        )
        compute_pass.end()
        self.device.queue.submit([command_encoder.finish()])
        
        # Read back coherence field for visualization update
        # (In production, use staging buffer for efficient readback.)
        self.coherence_field = np.frombuffer(
            self.coherence_buffer.read_mapped(0, self.total_cells * 4),
            dtype=np.float32
        ).copy()
        
        # Update texture
        self.texture.data[:] = self.coherence_field.reshape(
            self.config.grid_size, self.config.grid_size, 1
        )
        self.texture.update_range((0, 0, 0), self.texture.size)
        
        # Render
        self.renderer.render(self.scene, self.camera)
        
        # Advance simulation parameter
        self.simulation_time += self.config.time_step
        
        # Callback for external observers
        if self._on_update:
            self._on_update(self)
            
    def set_on_update(self, callback: Callable):
        """Register callback for post-update processing."""
        self._on_update = callback
        
    def get_statistics(self) -> dict:
        """Compute field statistics for analysis."""
        phi = self.coherence_field
        return {
            "mean_coherence": float(np.mean(phi)),
            "std_coherence": float(np.std(phi)),
            "min_coherence": float(np.min(phi)),
            "max_coherence": float(np.max(phi)),
            "rtz_violations": int(np.sum(phi < self.config.rtz_floor)),
            "causal_order": self.config.causal_order,
            "simulation_time": self.simulation_time,
        }
