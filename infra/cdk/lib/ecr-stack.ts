import * as cdk from 'aws-cdk-lib';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { Construct } from 'constructs';

export interface EcrStackProps extends cdk.StackProps {
  environment: string;
}

/**
 * ECR Stack - Container Registry
 * 
 * Backend/Frontend用のECRリポジトリを構築
 */
export class EcrStack extends cdk.Stack {
  public readonly backendRepository: ecr.Repository;
  public readonly frontendRepository: ecr.Repository;

  constructor(scope: Construct, id: string, props: EcrStackProps) {
    super(scope, id, props);

    const { environment } = props;

    // ===========================================
    // Backend ECR Repository
    // ===========================================
    this.backendRepository = new ecr.Repository(this, 'BackendRepo', {
      repositoryName: `agentcore-poc-backend-${environment}`,
      removalPolicy: environment === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
      emptyOnDelete: environment !== 'prod',
      imageScanOnPush: true,
      lifecycleRules: [
        {
          rulePriority: 1,
          description: 'Keep last 10 images',
          maxImageCount: 10,
        },
      ],
    });

    // ===========================================
    // Frontend ECR Repository
    // ===========================================
    this.frontendRepository = new ecr.Repository(this, 'FrontendRepo', {
      repositoryName: `agentcore-poc-frontend-${environment}`,
      removalPolicy: environment === 'prod'
        ? cdk.RemovalPolicy.RETAIN
        : cdk.RemovalPolicy.DESTROY,
      emptyOnDelete: environment !== 'prod',
      imageScanOnPush: true,
      lifecycleRules: [
        {
          rulePriority: 1,
          description: 'Keep last 10 images',
          maxImageCount: 10,
        },
      ],
    });

    // ===========================================
    // Outputs
    // ===========================================
    new cdk.CfnOutput(this, 'BackendRepoUri', {
      value: this.backendRepository.repositoryUri,
      exportName: `${id}-BackendRepoUri`,
    });

    new cdk.CfnOutput(this, 'FrontendRepoUri', {
      value: this.frontendRepository.repositoryUri,
      exportName: `${id}-FrontendRepoUri`,
    });
  }
}

