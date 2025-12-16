import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface EcsStackProps extends cdk.StackProps {
  environment: string;
  backendRepository: ecr.Repository;
  frontendRepository: ecr.Repository;
  eventTable: dynamodb.Table;
  eventBus: events.EventBus;
  /** AgentCore Runtime ARN (optional) - 設定するとAgentCore Runtime経由で接続 */
  agentRuntimeArn?: string;
}

/**
 * ECS Stack - Fargate Service
 * 
 * Backend/FrontendをECS Fargateで実行
 */
export class EcsStack extends cdk.Stack {
  public readonly cluster: ecs.Cluster;
  public readonly backendService: ecs.FargateService;
  public readonly frontendService: ecs.FargateService;
  public readonly alb: elbv2.ApplicationLoadBalancer;

  constructor(scope: Construct, id: string, props: EcsStackProps) {
    super(scope, id, props);

    const {
      environment,
      backendRepository,
      frontendRepository,
      eventTable,
      eventBus,
      agentRuntimeArn,
    } = props;

    // ===========================================
    // VPC
    // ===========================================
    const vpc = new ec2.Vpc(this, 'Vpc', {
      vpcName: `agentcore-poc-vpc-${environment}`,
      maxAzs: 2,
      natGateways: environment === 'prod' ? 2 : 1,
    });

    // ===========================================
    // ECS Cluster
    // ===========================================
    this.cluster = new ecs.Cluster(this, 'Cluster', {
      clusterName: `agentcore-poc-${environment}`,
      vpc,
      containerInsights: true,
    });

    // ===========================================
    // Application Load Balancer
    // ===========================================
    this.alb = new elbv2.ApplicationLoadBalancer(this, 'ALB', {
      vpc,
      internetFacing: true,
      loadBalancerName: `agentcore-poc-alb-${environment}`,
    });

    // ===========================================
    // Backend Task Definition
    // ===========================================
    const backendTaskDef = new ecs.FargateTaskDefinition(this, 'BackendTaskDef', {
      memoryLimitMiB: 1024,
      cpu: 512,
    });

    // Bedrock permissions (Direct Bedrock fallback)
    backendTaskDef.addToTaskRolePolicy(
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
    backendTaskDef.addToTaskRolePolicy(
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

    // DynamoDB permissions
    eventTable.grantReadWriteData(backendTaskDef.taskRole);

    // EventBridge permissions
    backendTaskDef.addToTaskRolePolicy(
      new iam.PolicyStatement({
        actions: ['events:PutEvents'],
        resources: [eventBus.eventBusArn],
      })
    );

    // Backend環境変数を構築
    const backendEnvironment: Record<string, string> = {
      ENVIRONMENT: environment,
      AGENT_TYPE: 'strands',
      EVENT_TABLE_NAME: eventTable.tableName,
      EVENT_BUS_NAME: eventBus.eventBusName,
      AWS_REGION: this.region,
    };

    // AgentCore Runtime ARNが設定されている場合は環境変数に追加
    if (agentRuntimeArn) {
      backendEnvironment.AGENT_RUNTIME_ARN = agentRuntimeArn;
    }

    const backendContainer = backendTaskDef.addContainer('backend', {
      image: ecs.ContainerImage.fromEcrRepository(backendRepository, 'latest'),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'backend',
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
      environment: backendEnvironment,
      portMappings: [{ containerPort: 8000 }],
    });

    // ===========================================
    // Backend Service
    // ===========================================
    this.backendService = new ecs.FargateService(this, 'BackendService', {
      cluster: this.cluster,
      taskDefinition: backendTaskDef,
      serviceName: `agentcore-poc-backend-${environment}`,
      desiredCount: environment === 'prod' ? 2 : 1,
      assignPublicIp: false,
    });

    // ALB Target Group for Backend
    const backendTargetGroup = new elbv2.ApplicationTargetGroup(this, 'BackendTG', {
      vpc,
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/health',
        interval: cdk.Duration.seconds(30),
      },
    });

    this.backendService.attachToApplicationTargetGroup(backendTargetGroup);

    // ===========================================
    // Frontend Task Definition
    // ===========================================
    const frontendTaskDef = new ecs.FargateTaskDefinition(this, 'FrontendTaskDef', {
      memoryLimitMiB: 512,
      cpu: 256,
    });

    frontendTaskDef.addContainer('frontend', {
      image: ecs.ContainerImage.fromEcrRepository(frontendRepository, 'latest'),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'frontend',
        logRetention: logs.RetentionDays.ONE_WEEK,
      }),
      environment: {
        NEXT_PUBLIC_API_URL: `http://${this.alb.loadBalancerDnsName}/api`,
      },
      portMappings: [{ containerPort: 3000 }],
    });

    // ===========================================
    // Frontend Service
    // ===========================================
    this.frontendService = new ecs.FargateService(this, 'FrontendService', {
      cluster: this.cluster,
      taskDefinition: frontendTaskDef,
      serviceName: `agentcore-poc-frontend-${environment}`,
      desiredCount: environment === 'prod' ? 2 : 1,
      assignPublicIp: false,
    });

    // ALB Target Group for Frontend
    const frontendTargetGroup = new elbv2.ApplicationTargetGroup(this, 'FrontendTG', {
      vpc,
      port: 3000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/',
        interval: cdk.Duration.seconds(30),
      },
    });

    this.frontendService.attachToApplicationTargetGroup(frontendTargetGroup);

    // ===========================================
    // ALB Listener
    // ===========================================
    const listener = this.alb.addListener('HttpListener', {
      port: 80,
      defaultTargetGroups: [frontendTargetGroup],
    });

    // API routes to backend
    listener.addTargetGroups('ApiRoutes', {
      targetGroups: [backendTargetGroup],
      priority: 10,
      conditions: [
        elbv2.ListenerCondition.pathPatterns(['/api/*', '/health', '/sessions*', '/agents*']),
      ],
    });

    // ===========================================
    // Outputs
    // ===========================================
    new cdk.CfnOutput(this, 'AlbDnsName', {
      value: this.alb.loadBalancerDnsName,
      exportName: `${id}-AlbDnsName`,
    });

    new cdk.CfnOutput(this, 'ClusterName', {
      value: this.cluster.clusterName,
      exportName: `${id}-ClusterName`,
    });
  }
}

