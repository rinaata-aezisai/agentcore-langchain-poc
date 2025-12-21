#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { EventStoreStack } from '../lib/event-store-stack';
import { EcrStack } from '../lib/ecr-stack';
import { EcsStack } from '../lib/ecs-stack';
import { ServicesStack } from '../lib/services-stack';

const app = new cdk.App();

// 環境設定
const environment = app.node.tryGetContext('environment') || 'dev';
const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';

const env = { account, region };

const commonTags = {
  Project: 'agentcore-langchain-poc',
  Environment: environment,
  ManagedBy: 'CDK',
};

// ===========================================
// Services Stack (AgentCore + LangChain)
// 新しいシンプルなアーキテクチャ
// ===========================================
const servicesStack = new ServicesStack(app, `AgentCorePoc-Services-${environment}`, {
  env,
  environment,
  description: 'AgentCore and LangChain services for comparison PoC',
  tags: commonTags,
});

// ===========================================
// Event Store Stack (DynamoDB + EventBridge)
// オプション: イベントソーシングが必要な場合
// ===========================================
const eventStoreStack = new EventStoreStack(app, `AgentCorePoc-EventStore-${environment}`, {
  env,
  environment,
  description: 'Event Sourcing infrastructure for AgentCore vs LangChain PoC',
  tags: commonTags,
});

// ===========================================
// ECR Stack (Container Registries) - レガシー
// ===========================================
const ecrStack = new EcrStack(app, `AgentCorePoc-ECR-${environment}`, {
  env,
  environment,
  description: 'ECR repositories for AgentCore vs LangChain PoC',
  tags: commonTags,
});

// ===========================================
// ECS Stack (Fargate Services) - レガシー
// ===========================================
const ecsStack = new EcsStack(app, `AgentCorePoc-ECS-${environment}`, {
  env,
  environment,
  backendRepository: ecrStack.backendRepository,
  frontendRepository: ecrStack.frontendRepository,
  eventTable: eventStoreStack.eventTable,
  eventBus: eventStoreStack.eventBus,
  description: 'ECS Fargate services for AgentCore vs LangChain PoC',
  tags: commonTags,
});

ecsStack.addDependency(eventStoreStack);
ecsStack.addDependency(ecrStack);

app.synth();
