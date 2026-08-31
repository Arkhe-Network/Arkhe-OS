// coherence-dashboard.component.ts
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
    `.value { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 2em; }`,
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
  }

  loadHandovers() {
    const headers = new HttpHeaders().set('Authorization', `Bearer ${localStorage.getItem('token')}`);
    this.http.get(`/api/handovers/project/${this.projectId}?limit=50`, { headers })
      .subscribe((data: any) => {
        this.handovers = data;
        if (data.length > 0) {
          this.currentCoherence = data[0].coherence;
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
    };
  }
}