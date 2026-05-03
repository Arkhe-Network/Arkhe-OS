"""
Observer 5D Interface — Causal Order Control Widget
Allows smooth interpolation between causal regimes.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from core.temporal.causal_order_simulator import CausalOrderSimulator, CausalOrderConfig

class CausalOrderController:
    """Interactive controller for causal order simulation."""
    
    def __init__(self, simulator: CausalOrderSimulator):
        self.simulator = simulator
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        plt.subplots_adjust(bottom=0.15)
        
        # Initial visualization
        self.im = self.ax.imshow(
            simulator.coherence_field.reshape(simulator.config.grid_size, -1),
            cmap=simulator.config.color_map,
            vmin=0, vmax=1,
            interpolation='nearest'
        )
        self.ax.set_title("Coherence Field — Causal Order: 0.0 (Atemporal)")
        self.ax.set_xlabel("Spatial Dimension X")
        self.ax.set_ylabel("Spatial Dimension Y")
        
        # Causal order slider
        ax_slider = plt.axes([0.15, 0.05, 0.7, 0.04])
        self.slider = Slider(
            ax_slider, "Causal Order", -1.0, 1.0, 
            valinit=0.0, valfmt="%0.2f", color='lightblue'
        )
        self.slider.on_changed(self._on_causal_order_change)
        
        # Regime indicators
        self.regime_text = self.ax.text(
            0.02, 0.98, "", transform=self.ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )
        
        # Statistics display
        self.stats_text = self.ax.text(
            0.98, 0.98, "", transform=self.ax.transAxes,
            fontsize=8, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5)
        )
        
        # Reset button
        ax_reset = plt.axes([0.8, 0.05, 0.1, 0.04])
        self.reset_btn = Button(ax_reset, "Reset", color='lightgoldenrodyellow')
        self.reset_btn.on_clicked(self._on_reset)
        
        # Animation control
        self.running = False
        self._animation_id = None
        
        # Register update callback
        simulator.set_on_update(self._on_simulation_update)
        
    def _on_causal_order_change(self, val: float):
        """Handle causal order slider change."""
        self.simulator.update(causal_order=val)
        self._update_regime_label(val)
        
    def _update_regime_label(self, causal_order: float):
        """Update regime description based on causal order."""
        if abs(causal_order) < 0.1:
            regime = "🌀 ATEMPORAL\n(Bilateral Fisher-Rao)"
            color = 'cyan'
        elif causal_order < 0:
            regime = "⬅️ PAST→FUTURE\n(Standard Causality)"
            color = 'lightblue'
        else:
            regime = "➡️ FUTURE→PAST\n(Reversed Causality)"
            color = 'lightcoral'
        
        self.regime_text.set_text(regime)
        self.regime_text.get_bbox_patch().set_facecolor(color)
        self.ax.set_title(f"Coherence Field — Causal Order: {causal_order:+.2f}")
        
    def _on_simulation_update(self, simulator):
        """Callback after each simulation step."""
        # Update visualization
        self.im.set_data(
            simulator.coherence_field.reshape(simulator.config.grid_size, -1)
        )
        
        # Update statistics
        stats = simulator.get_statistics()
        stats_str = (
            f"μ={stats['mean_coherence']:.3f}\n"
            f"σ={stats['std_coherence']:.3f}\n"
            f"min={stats['min_coherence']:.3f}\n"
            f"t={stats['simulation_time']:.2f}"
        )
        self.stats_text.set_text(stats_str)
        
        # Redraw
        self.fig.canvas.draw_idle()
        
    def _on_reset(self, event):
        """Reset simulation to initial state."""
        self.simulator.coherence_field[:] = 0.5
        self.simulator.phase_field[:] = 0.0
        self.simulator.simulation_time = 0.0
        self.slider.reset()
        self._on_simulation_update(self.simulator)
        
    def toggle_animation(self):
        """Start/stop continuous simulation."""
        if self.running:
            if self._animation_id:
                self.fig.canvas.manager.timer.remove(self._animation_id)
            self.running = False
        else:
            def animate():
                self.simulator.update()
                return True
            self._animation_id = self.fig.canvas.manager.timer.create(
                50, animate, repeat=True
            )
            self.running = True
            
    def show(self):
        """Display interactive controller."""
        print("🌀 ARKHE OS v∞.430.1 — Causal Order Simulator")
        print("Controls:")
        print("  • Slider: Adjust causal order (-1.0 to +1.0)")
        print("  • Reset: Return to initial state")
        print("  • Space: Toggle animation")
        print("\nRegimes:")
        print("  • -1.0: Standard causality (past→future)")
        print("  •  0.0: Atemporal (bilateral Fisher-Rao)")
        print("  • +1.0: Reversed causality (future→past)")
        print("\n🔮 The field is static. Your attention creates the flow.")
        
        # Bind spacebar to toggle animation
        def on_key(event):
            if event.key == ' ':
                self.toggle_animation()
                
        self.fig.canvas.mpl_connect('key_press_event', on_key)
        plt.show()
