import { defineFunction } from '@aws-amplify/backend';

/**
 * Service API Lambda Function
 * 
 * AgentCore vs LangChain のサービステスト用API
 */
export const serviceApi = defineFunction({
  name: 'service-api',
  entry: './handler.ts',
  timeoutSeconds: 60,
  memoryMB: 512,
  environment: {
    BEDROCK_MODEL_ID: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
  },
});

