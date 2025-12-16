#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { EventStoreStack } from '../lib/event-store-stack';
import { ApiStack } from '../lib/api-stack';

const app = new cdk.App();

// 環境設定
const environment = app.node.tryGetContext('environment') || 'dev';
const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';

const env = { account, region };

// ===========================================
// Event Store Stack (DynamoDB + EventBridge)
// ===========================================
const eventStoreStack = new EventStoreStack(app, `AgentCorePoc-EventStore-${environment}`, {
  env,
  environment,
  description: 'Event Sourcing infrastructure for AgentCore vs LangChain PoC',
  tags: {
    Project: 'agentcore-langchain-poc',
    Environment: environment,
  },
});

// ===========================================
// API Stack (Lambda + API Gateway)
// ===========================================
const apiStack = new ApiStack(app, `AgentCorePoc-Api-${environment}`, {
  env,
  environment,
  eventTable: eventStoreStack.eventTable,
  eventBus: eventStoreStack.eventBus,
  description: 'API infrastructure for AgentCore vs LangChain PoC',
  tags: {
    Project: 'agentcore-langchain-poc',
    Environment: environment,
  },
});

apiStack.addDependency(eventStoreStack);

app.synth();

