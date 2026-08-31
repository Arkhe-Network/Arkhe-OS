// src/models/handover.model.ts
import {Entity, model, property, belongsTo} from '@loopback/repository';
import {User} from './user.model';
import {Project} from './project.model';

@model({
  settings: {
    postgresql: {table: 'handovers'},
    indexes: {
      idx_coherence: {keys: {coherence: 1}},
      idx_timestamp: {keys: {timestamp: -1}}
    }
  }
})
export class Handover extends Entity {
  @property({id: true, generated: true})
  id: string;

  @property({type: 'number', required: true})
  coherence: number;      // Coerência do handover (0..1)

  @property({type: 'number', required: true})
  phase: number;           // Fase φ (radianos)

  @property({type: 'string'})
  gamma_b: string;         // Fase genômica (JSON serializado)

  @property({type: 'date', required: true})
  timestamp: Date;         // Timestamp do handover (T1)

  @property({type: 'number'})
  stability_index: number; // Estabilidade do sistema

  @property({type: 'object'})
  metadata: object;        // Dados adicionais (Z_g, p_error, etc.)

  @belongsTo(() => Project)
  projectId: string;

  @belongsTo(() => User)
  createdBy: string;

  constructor(data?: Partial<Handover>) {
    super(data);
  }
}