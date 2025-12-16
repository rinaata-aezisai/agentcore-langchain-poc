import { defineAuth } from '@aws-amplify/backend';

/**
 * AWS Cognito User Pool設定
 * 
 * Amplify Gen2のファイルベース設定
 */
export const auth = defineAuth({
  loginWith: {
    email: true,
  },
  // パスワードポリシー
  userAttributes: {
    email: {
      required: true,
      mutable: true,
    },
    preferredUsername: {
      required: false,
      mutable: true,
    },
  },
});

