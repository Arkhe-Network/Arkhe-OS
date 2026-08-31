// src/services/sqs.service.ts
import {injectable, inject} from '@loopback/core';
import {SQSClient, SendMessageCommand} from '@aws-sdk/client-sqs';
import {config} from '../config/aws.config';

@injectable()
export class SqsService {
  private client: SQSClient;
  private queueUrl: string;

  constructor() {
    this.client = new SQSClient({
      region: config.aws.region,
      credentials: config.aws.credentials,
    });
    this.queueUrl = config.aws.sqs.handoverQueueUrl;
  }

  async sendMessage(payload: any): Promise<void> {
    const command = new SendMessageCommand({
      QueueUrl: this.queueUrl,
      MessageBody: JSON.stringify(payload),
      MessageAttributes: {
        Type: {
          DataType: 'String',
          StringValue: payload.type || 'HANDOVER_CREATED',
        },
      },
    });
    await this.client.send(command);
    console.log(`📤 Mensagem enviada para SQS: ${payload.type}`);
  }
}