import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface ApiStackProps extends cdk.StackProps {
  environment: string;
  eventTable: dynamodb.Table;
  eventBus: events.EventBus;
  /** AgentCore Runtime ARN (optional) - 設定するとAgentCore Runtime経由で接続 */
  agentRuntimeArn?: string;
}

/**
 * API Gateway + Lambda Stack
 * 
 * FastAPI バックエンドをLambdaでホスト
 */
export class ApiStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;
  public readonly backendFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    const { environment, eventTable, eventBus, agentRuntimeArn } = props;

    // ===========================================
    // Lambda Function for Backend
    // ===========================================
    this.backendFunction = new lambda.Function(this, 'BackendFunction', {
      functionName: `agentcore-poc-backend-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'mangum_handler.handler',
      code: lambda.Code.fromAsset('../../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -r src/* /asset-output/',
          ],
        },
      }),
      timeout: cdk.Duration.seconds(30),
      memorySize: 1024,
      environment: {
        EVENT_TABLE_NAME: eventTable.tableName,
        EVENT_BUS_NAME: eventBus.eventBusName,
        AGENT_TYPE: 'strands',  // or 'langchain'
        AWS_REGION_NAME: this.region,
        LOG_LEVEL: environment === 'prod' ? 'INFO' : 'DEBUG',
        // AgentCore Runtime ARN (設定されている場合はAgentCore Runtime経由で接続)
        ...(agentRuntimeArn && { AGENT_RUNTIME_ARN: agentRuntimeArn }),
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // DynamoDB permissions
    eventTable.grantReadWriteData(this.backendFunction);

    // EventBridge permissions
    this.backendFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['events:PutEvents'],
        resources: [eventBus.eventBusArn],
      })
    );

    // Bedrock permissions (Direct Bedrock fallback)
    this.backendFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['*'],
      })
    );

    // AgentCore Runtime permissions (本番推奨)
    // invoke_agent_runtime() でECRにデプロイされたエージェントを呼び出す
    this.backendFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock-agentcore:InvokeAgentRuntime',
          'bedrock-agentcore:InvokeAgentRuntimeForUser',
        ],
        resources: agentRuntimeArn 
          ? [agentRuntimeArn, `${agentRuntimeArn}/*`]
          : ['*'],
      })
    );

    // ===========================================
    // API Gateway
    // ===========================================
    this.api = new apigateway.RestApi(this, 'AgentApi', {
      restApiName: `agentcore-poc-api-${environment}`,
      description: 'AgentCore vs LangChain PoC API',
      deployOptions: {
        stageName: environment,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: environment !== 'prod',
        metricsEnabled: true,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token',
        ],
      },
    });

    // Lambda integration
    const lambdaIntegration = new apigateway.LambdaIntegration(
      this.backendFunction,
      {
        proxy: true,
      }
    );

    // Proxy all requests to Lambda
    this.api.root.addProxy({
      defaultIntegration: lambdaIntegration,
      anyMethod: true,
    });

    // ===========================================
    // Outputs
    // ===========================================
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: this.api.url,
      exportName: `${id}-ApiUrl`,
    });

    new cdk.CfnOutput(this, 'BackendFunctionArn', {
      value: this.backendFunction.functionArn,
      exportName: `${id}-BackendFunctionArn`,
    });
  }
}

