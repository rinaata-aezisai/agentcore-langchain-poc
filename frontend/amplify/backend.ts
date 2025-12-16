import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { Effect, PolicyStatement } from 'aws-cdk-lib/aws-iam';

/**
 * Amplify Gen2 Backend定義
 * 
 * 認証とデータ（GraphQL）を設定
 */
export const backend = defineBackend({
  auth,
  data,
});

// 認証済みユーザーにBedrockアクセス権限を付与
const bedrockPolicy = new PolicyStatement({
  effect: Effect.ALLOW,
  actions: [
    'bedrock:InvokeModel',
    'bedrock:InvokeModelWithResponseStream',
  ],
  resources: [
    'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-*',
  ],
});

backend.auth.resources.authenticatedUserIamRole.addToPrincipalPolicy(bedrockPolicy);
