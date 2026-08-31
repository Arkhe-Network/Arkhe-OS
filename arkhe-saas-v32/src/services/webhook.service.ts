// src/services/webhook.service.ts
import {injectable} from '@loopback/core';
import axios from 'axios';

@injectable()
export class WebhookService {
  private subscriptions: Map<string, string[]> = new Map();

  // Registra endpoints para eventos
  registerSubscription(event: string, url: string): void {
    if (!this.subscriptions.has(event)) {
      this.subscriptions.set(event, []);
    }
    this.subscriptions.get(event)!.push(url);
  }

  async trigger(event: string, payload: any): Promise<void> {
    const urls = this.subscriptions.get(event) || [];
    const promises = urls.map(async (url) => {
      try {
        await axios.post(url, payload, {
          headers: {'Content-Type': 'application/json'},
          timeout: 5000,
        });
        console.log(`✅ Webhook enviado para ${url} (evento: ${event})`);
      } catch (err: any) {
        console.error(`❌ Falha ao enviar webhook para ${url}: ${err.message}`);
      }
    });
    await Promise.allSettled(promises);
  }
}