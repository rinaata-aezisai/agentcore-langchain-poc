import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { serviceApi } from './functions/service-api/resource';
import { Effect, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { FunctionUrlAuthType } from 'aws-cdk-lib/aws-lambda';

/**
 * Amplify Gen2 Backend定義
 * 
 * 認証、データ（GraphQL）、サービスAPI（Lambda）を設定
 */
export const backend = defineBackend({
  auth,
  data,
  serviceApi,
});

// 認証済みユーザーにBedrockアクセス権限を付与
const bedrockPolicy = new PolicyStatement({
  effect: Effect.ALLOW,
  actions: [
    'bedrock:InvokeModel',
    'bedrock:InvokeModelWithResponseStream',
    'bedrock:Converse',
    'bedrock:ConverseStream',
  ],
  resources: [
    'arn:aws:bedrock:*::foundation-model/anthropic.claude-*',
    'arn:aws:bedrock:*::foundation-model/us.anthropic.claude-*',
  ],
});

backend.auth.resources.authenticatedUserIamRole.addToPrincipalPolicy(bedrockPolicy);

// Lambda関数にもBedrockアクセス権限を付与
backend.serviceApi.resources.lambda.addToRolePolicy(bedrockPolicy);

// Lambda Function URL を追加（API Gatewayの代わりにシンプルなエンドポイント）
const functionUrl = backend.serviceApi.resources.lambda.addFunctionUrl({
  authType: FunctionUrlAuthType.NONE,
  cors: {
    allowedOrigins: ['*'],
    allowedHeaders: ['*'],
  },
});

// Output the Function URL
backend.addOutput({
  custom: {
    serviceApiUrl: functionUrl.url,
  },
});
