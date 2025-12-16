'use client';

import { Amplify, ResourcesConfig } from 'aws-amplify';

/**
 * Amplify設定
 * 
 * amplify_outputs.jsonから自動生成された値を使用
 */

// デプロイ済みの設定値
const DEPLOYED_CONFIG = {
  userPoolId: 'ap-northeast-1_urcbai3PM',
  userPoolClientId: '68ua0f2mh6ou8qs9r2nonqeueb',
  identityPoolId: 'ap-northeast-1:cceb6495-abb4-441a-88e3-bf7440ca0a2c',
  region: 'ap-northeast-1',
};

export function configureAmplify() {
  const config: ResourcesConfig = {
    Auth: {
      Cognito: {
        userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID || DEPLOYED_CONFIG.userPoolId,
        userPoolClientId: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID || DEPLOYED_CONFIG.userPoolClientId,
        identityPoolId: process.env.NEXT_PUBLIC_IDENTITY_POOL_ID || DEPLOYED_CONFIG.identityPoolId,
        loginWith: {
          email: true,
        },
        signUpVerificationMethod: 'code',
        userAttributes: {
          email: {
            required: true,
          },
        },
        allowGuestAccess: true,
        passwordFormat: {
          minLength: 8,
          requireLowercase: true,
          requireUppercase: true,
          requireNumbers: true,
          requireSpecialCharacters: true,
        },
      },
    },
  };

  Amplify.configure(config, { ssr: true });
}

// API設定
export const apiConfig = {
  endpoint: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  bedrockRegion: process.env.NEXT_PUBLIC_BEDROCK_REGION || 'ap-northeast-1',
  bedrockModelId: process.env.NEXT_PUBLIC_BEDROCK_MODEL_ID || 'anthropic.claude-3-haiku-20240307-v1:0',
};
