import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';

export interface EventStoreStackProps extends cdk.StackProps {
  environment: string;
}

/**
 * Event Sourcing Infrastructure Stack
 * 
 * DynamoDB Event Store と EventBridge を構築
 */
export class EventStoreStack extends cdk.Stack {
  public readonly eventTable: dynamodb.Table;
  public readonly eventBus: events.EventBus;

  constructor(scope: Construct, id: string, props: EventStoreStackProps) {
    super(scope, id, props);

    const { environment } = props;

    // ===========================================
    // DynamoDB Event Store
    // ===========================================
    this.eventTable = new dynamodb.Table(this, 'EventStore', {
      tableName: `agentcore-poc-events-${environment}`,
      partitionKey: {
        name: 'PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'SK',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: environment === 'prod' 
        ? cdk.RemovalPolicy.RETAIN 
        : cdk.RemovalPolicy.DESTROY,
      pointInTimeRecovery: environment === 'prod',
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
    });

    // GSI for querying by event type
    this.eventTable.addGlobalSecondaryIndex({
      indexName: 'GSI1',
      partitionKey: {
        name: 'GSI1PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'GSI1SK',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // ===========================================
    // EventBridge Event Bus
    // ===========================================
    this.eventBus = new events.EventBus(this, 'AgentEventBus', {
      eventBusName: `agentcore-poc-events-${environment}`,
    });

    // Archive for event replay
    this.eventBus.archive('EventArchive', {
      archiveName: `agentcore-poc-archive-${environment}`,
      retention: cdk.Duration.days(environment === 'prod' ? 365 : 30),
      eventPattern: {
        source: ['agentcore-poc'],
      },
    });

    // ===========================================
    // Outputs
    // ===========================================
    new cdk.CfnOutput(this, 'EventTableName', {
      value: this.eventTable.tableName,
      exportName: `${id}-EventTableName`,
    });

    new cdk.CfnOutput(this, 'EventTableArn', {
      value: this.eventTable.tableArn,
      exportName: `${id}-EventTableArn`,
    });

    new cdk.CfnOutput(this, 'EventBusName', {
      value: this.eventBus.eventBusName,
      exportName: `${id}-EventBusName`,
    });

    new cdk.CfnOutput(this, 'EventBusArn', {
      value: this.eventBus.eventBusArn,
      exportName: `${id}-EventBusArn`,
    });
  }
}


