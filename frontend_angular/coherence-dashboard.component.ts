// frontend_angular/coherence-dashboard.component.ts
import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-coherence-dashboard',
  template: `
    <div class="dashboard">
      <h2>🕊️ Coerência do Orbe (Projeto: {{ projectId }})</h2>
      <div class="gauge">
        <canvas id="coherenceGauge" width="200" height="200"></canvas>
        <span class="value">{{ currentCoherence | number:'1.4-4' }}</span>
      </div>
      <div class="toon-viewer">
        <h3>Visualização TOON 3D</h3>
        <div id="toon-container" style="width: 100%; height: 300px; background-color: #000; border: 1px solid #333;">
           <!-- Three.js renderer will be injected here -->
           <p style="color: #0f0; text-align: center; padding-top: 140px;">TOON 3D Renderer Placeholder</p>
        </div>
      </div>
      <div class="history">
        <h3>Histórico de Handovers</h3>
        <table>
          <tr *ngFor="let h of handovers | slice:0:20">
            <td>{{ h.timestamp | date:'short' }}</td>
            <td>{{ h.coherence | number:'1.4-4' }}</td>
            <td>{{ h.stability_index | number:'1.4-4' }}</td>
          </tr>
        </table>
      </div>
    </div>
  `,
  styles: [
    `.gauge { position: relative; display: inline-block; }`,
    `.value { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 2em; color: white; }`,
    `.dashboard { color: #fff; background-color: #111; padding: 20px; font-family: monospace; }`,
    `table { width: 100%; border-collapse: collapse; }`,
    `td, th { border: 1px solid #444; padding: 8px; text-align: left; }`
  ]
})
export class CoherenceDashboardComponent implements OnInit {
  projectId = 'proj-123';
  currentCoherence = 0.965;
  handovers: any[] = [];

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadHandovers();
    this.subscribeToRealtime();
    this.initToonViewer();
  }

  loadHandovers() {
    const headers = new HttpHeaders().set('Authorization', `Bearer ${localStorage.getItem('token')}`);
    this.http.get(`/api/handovers/project/${this.projectId}?limit=50`, { headers })
      .subscribe((data: any) => {
        this.handovers = data;
        if (data.length > 0) {
          this.currentCoherence = data[0].coherence;
          this.updateToon(data[0]);
        }
      });
  }

  subscribeToRealtime() {
    // WebSocket ou SSE para atualizações em tempo real
    const eventSource = new EventSource(`/api/sse/project/${this.projectId}`);
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.currentCoherence = data.coherence;
      this.handovers.unshift(data);
      this.updateToon(data);
    };
  }

  scene!: THREE.Scene;
  camera!: THREE.PerspectiveCamera;
  renderer!: THREE.WebGLRenderer;
  mesh!: THREE.Mesh;

  initToonViewer() {
    console.log("Initializing TOON 3D Viewer");

    // Dynamic import to avoid SSR issues if applicable, though typically imported top-level
    import('three').then(THREE => {
      const container = document.getElementById('toon-container');
      if (!container) return;

      container.innerHTML = ''; // Clear placeholder

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);

      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.renderer.setSize(container.clientWidth, container.clientHeight);
      container.appendChild(this.renderer.domElement);

      const geometry = new THREE.TorusKnotGeometry(10, 3, 100, 16);

      // A Toon-like material
      const material = new THREE.MeshToonMaterial({
        color: 0x00ff88,
        wireframe: false
      });

      this.mesh = new THREE.Mesh(geometry, material);
      this.scene.add(this.mesh);

      const light = new THREE.DirectionalLight(0xffffff, 1);
      light.position.set(1, 1, 1).normalize();
      this.scene.add(light);

      const ambientLight = new THREE.AmbientLight(0x404040); // soft white light
      this.scene.add(ambientLight);

      this.camera.position.z = 30;

      const animate = () => {
        requestAnimationFrame(animate);
        if (this.mesh) {
          this.mesh.rotation.x += 0.01;
          this.mesh.rotation.y += 0.01;
        }
        this.renderer.render(this.scene, this.camera);
      };

      animate();
    });
  }

  updateToon(handoverData: any) {
     console.log("Updating TOON 3D with new data", handoverData);
     if (this.mesh && handoverData.phase) {
        // Example dynamic adjustment based on handover phase
        import('three').then(THREE => {
            const scaleFactor = 1 + (handoverData.phase % 1.0); // simple visual change
            this.mesh.scale.set(scaleFactor, scaleFactor, scaleFactor);
            // Change color based on coherence
            if (handoverData.coherence < 0.8) {
               (this.mesh.material as THREE.MeshToonMaterial).color.setHex(0xff4444); // Red
            } else if (handoverData.coherence < 0.95) {
               (this.mesh.material as THREE.MeshToonMaterial).color.setHex(0xffaa00); // Yellow
            } else {
               (this.mesh.material as THREE.MeshToonMaterial).color.setHex(0x00ff88); // Green
            }
        });
     }
  }
}