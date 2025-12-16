import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';

/**
 * Amplify Gen2 Backend定義
 * 
 * 認証とデータ（GraphQL）を設定
 */
export const backend = defineBackend({
  auth,
  data,
});

// Bedrockアクセス用のIAMポリシーを追加
const bedrockPolicy = {
  Version: '2012-10-17',
  Statement: [
    {
      Effect: 'Allow',
      Action: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
      ],
      Resource: [
        'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-*',
      ],
    },
  ],
};

// 認証済みユーザーにBedrockアクセス権限を付与
backend.auth.resources.authenticatedUserIamRole.addToPrincipalPolicy({
  Effect: 'Allow',
  Action: [
    'bedrock:InvokeModel',
    'bedrock:InvokeModelWithResponseStream',
  ],
  Resource: [
    'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-*',
  ],
} as any);

