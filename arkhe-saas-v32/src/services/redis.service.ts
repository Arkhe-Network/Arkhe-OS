// src/services/redis.service.ts
import {injectable} from '@loopback/core';
import {createClient, RedisClientType} from 'redis';

@injectable()
export class RedisService {
  private client: RedisClientType;

  constructor() {
    this.client = createClient({
      url: process.env.REDIS_URL || 'redis://localhost:6379',
    });
    this.client.connect();
  }

  async get<T>(key: string): Promise<T | null> {
    const data = await this.client.get(key);
    return data ? JSON.parse(data) : null;
  }

  async set(key: string, value: any, ttl?: number): Promise<void> {
    await this.client.set(key, JSON.stringify(value));
    if (ttl) await this.client.expire(key, ttl);
  }

  // Para dados de coerência em tempo real (dashboard)
  async updateCoherence(projectId: string, coherence: number): Promise<void> {
    await this.client.set(`project:${projectId}:coherence`, coherence.toString());
  }

  async getCoherence(projectId: string): Promise<number | null> {
    const val = await this.client.get(`project:${projectId}:coherence`);
    return val ? parseFloat(val) : null;
  }
}