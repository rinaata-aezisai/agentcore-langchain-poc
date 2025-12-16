import { type ClientSchema, a, defineData } from '@aws-amplify/backend';

/**
 * GraphQL Schema定義
 * 
 * セッションとメッセージのスキーマ
 */
const schema = a.schema({
  // チャットセッション
  ChatSession: a
    .model({
      sessionId: a.string().required(),
      agentType: a.enum(['STRANDS', 'LANGCHAIN']),
      userId: a.string().required(),
      state: a.enum(['ACTIVE', 'ENDED', 'PAUSED']),
      messages: a.hasMany('ChatMessage', 'sessionId'),
      createdAt: a.datetime(),
      updatedAt: a.datetime(),
    })
    .authorization((allow) => [allow.owner()]),

  // チャットメッセージ
  ChatMessage: a
    .model({
      messageId: a.string().required(),
      sessionId: a.string().required(),
      role: a.enum(['USER', 'ASSISTANT', 'SYSTEM']),
      content: a.string().required(),
      toolCalls: a.json(),
      metadata: a.json(),
      latencyMs: a.integer(),
      session: a.belongsTo('ChatSession', 'sessionId'),
      createdAt: a.datetime(),
    })
    .authorization((allow) => [allow.owner()]),

  // ベンチマーク結果
  BenchmarkResult: a
    .model({
      resultId: a.string().required(),
      testName: a.string().required(),
      strandsLatencyMs: a.integer(),
      langchainLatencyMs: a.integer(),
      strandsSuccess: a.boolean(),
      langchainSuccess: a.boolean(),
      metadata: a.json(),
      createdAt: a.datetime(),
    })
    .authorization((allow) => [allow.authenticated()]),
});

export type Schema = ClientSchema<typeof schema>;

export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'userPool',
  },
});

