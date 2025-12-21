import type { Handler } from 'aws-lambda';
import {
  BedrockRuntimeClient,
  ConverseCommand,
} from '@aws-sdk/client-bedrock-runtime';

const client = new BedrockRuntimeClient({ region: 'us-east-1' });

interface ServiceExecuteRequest {
  instruction: string;
  agent_type: 'strands' | 'langchain';
  tools?: Record<string, unknown>[];
  use_memory?: boolean;
  session_id?: string;
}

interface ServiceExecuteResponse {
  response_id: string;
  content: string;
  tool_calls?: Record<string, unknown>[];
  latency_ms: number;
  metadata?: Record<string, unknown>;
  framework_features?: string[];
}

interface LambdaEvent {
  httpMethod?: string;
  requestContext?: {
    http?: {
      method: string;
      path: string;
    };
  };
  rawPath?: string;
  path?: string;
  body?: string;
  isBase64Encoded?: boolean;
}

interface LambdaResponse {
  statusCode: number;
  headers: Record<string, string>;
  body: string;
}

/**
 * Generate ULID-like ID
 */
function generateId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 12);
  return `${timestamp}${random}`.toUpperCase();
}

/**
 * Call Bedrock Converse API
 */
async function callBedrock(prompt: string): Promise<string> {
  const modelId = process.env.BEDROCK_MODEL_ID || 'anthropic.claude-3-5-sonnet-20241022-v2:0';
  
  try {
    const command = new ConverseCommand({
      modelId,
      messages: [
        {
          role: 'user',
          content: [{ text: prompt }],
        },
      ],
      inferenceConfig: {
        maxTokens: 1024,
        temperature: 0.7,
      },
    });

    const response = await client.send(command);
    
    const content = response.output?.message?.content?.[0];
    if (content && 'text' in content && content.text) {
      return content.text;
    }
    
    return 'No response generated.';
  } catch (error) {
    console.error('Bedrock API error:', error);
    return `Error calling Bedrock: ${error instanceof Error ? error.message : 'Unknown error'}`;
  }
}

/**
 * Get framework-specific features
 */
function getFrameworkFeatures(agentType: 'strands' | 'langchain'): string[] {
  if (agentType === 'strands') {
    return [
      'bedrock_native_integration',
      'agentcore_memory_api',
      'prompt_caching',
      'tool_caching',
      'automatic_tool_loop',
      'guardrails',
    ];
  }
  return [
    'langgraph_state_management',
    'checkpointing',
    'tool_node_automation',
    'multi_provider_support',
    'time_travel_debugging',
  ];
}

/**
 * Main handler
 */
export const handler: Handler<LambdaEvent, LambdaResponse> = async (event) => {
  // CORS headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  };

  // Get HTTP method and path (works with both API Gateway and Function URL)
  const method = event.requestContext?.http?.method || event.httpMethod || 'GET';
  const path = event.requestContext?.http?.path || event.rawPath || event.path || '/';

  console.log(`Request: ${method} ${path}`);

  // Handle OPTIONS (CORS preflight)
  if (method === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  try {
    // Parse body
    let body: ServiceExecuteRequest | undefined;
    if (event.body) {
      const rawBody = event.isBase64Encoded 
        ? Buffer.from(event.body, 'base64').toString('utf-8')
        : event.body;
      body = JSON.parse(rawBody);
    }

    // Health check
    if (path.endsWith('/health') || path === '/') {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ status: 'ok', version: '1.0.0', path }),
      };
    }

    // Service info
    if (path.includes('/info') && method === 'GET') {
      const serviceName = path.split('/services/')[1]?.split('/')[0] || 'runtime';
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          service: serviceName,
          description: `${serviceName} service for AgentCore vs LangChain comparison`,
          supported_agents: ['strands', 'langchain'],
          strands_features: getFrameworkFeatures('strands'),
          langchain_features: getFrameworkFeatures('langchain'),
          comparison_available: true,
        }),
      };
    }

    // Service execute
    if (path.includes('/execute') && method === 'POST' && body) {
      const startTime = Date.now();

      // Simulate agent-specific behavior
      let systemPrompt = '';
      if (body.agent_type === 'strands') {
        systemPrompt = 'You are an AI assistant powered by AWS Bedrock AgentCore (Strands Agents). ';
      } else {
        systemPrompt = 'You are an AI assistant powered by LangChain/LangGraph. ';
      }

      const fullPrompt = `${systemPrompt}\n\nUser: ${body.instruction}`;
      const content = await callBedrock(fullPrompt);
      
      const latencyMs = Date.now() - startTime;

      const response: ServiceExecuteResponse = {
        response_id: generateId(),
        content,
        latency_ms: latencyMs,
        metadata: {
          service: path.split('/services/')[1]?.split('/')[0] || 'runtime',
          agent_type: body.agent_type,
          model_id: process.env.BEDROCK_MODEL_ID,
        },
        framework_features: getFrameworkFeatures(body.agent_type),
      };

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify(response),
      };
    }

    // Service compare (run both)
    if (path.includes('/compare') && method === 'POST' && body) {
      // Run Strands
      const strandsStart = Date.now();
      const strandsPrompt = `You are an AI assistant powered by AWS Bedrock AgentCore (Strands Agents).\n\nUser: ${body.instruction}`;
      const strandsContent = await callBedrock(strandsPrompt);
      const strandsLatency = Date.now() - strandsStart;

      // Run LangChain
      const langchainStart = Date.now();
      const langchainPrompt = `You are an AI assistant powered by LangChain/LangGraph.\n\nUser: ${body.instruction}`;
      const langchainContent = await callBedrock(langchainPrompt);
      const langchainLatency = Date.now() - langchainStart;

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          strands_result: {
            response_id: generateId(),
            content: strandsContent,
            latency_ms: strandsLatency,
            framework_features: getFrameworkFeatures('strands'),
          },
          langchain_result: {
            response_id: generateId(),
            content: langchainContent,
            latency_ms: langchainLatency,
            framework_features: getFrameworkFeatures('langchain'),
          },
          comparison: {
            latency_diff_ms: strandsLatency - langchainLatency,
            faster_framework: strandsLatency < langchainLatency ? 'strands' : 'langchain',
          },
        }),
      };
    }

    // Not found
    return {
      statusCode: 404,
      headers,
      body: JSON.stringify({ error: 'Not found', path, method }),
    };
  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        error: error instanceof Error ? error.message : 'Unknown error',
      }),
    };
  }
};
