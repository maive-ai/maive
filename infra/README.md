# Infrastructure

This directory contains the Pulumi infrastructure code for deploying the Maive application to AWS GovCloud.

## Prerequisites

1. **AWS CLI configured** with GovCloud credentials
2. **Pulumi CLI** installed
3. **Docker** installed (for building images)
4. **Python 3.13+** with uv package manager

## Environment Strategy

This infrastructure supports two types of environments:

### Preview Environments (Ephemeral)
- **Purpose**: PR validation and infrastructure change review
- **Cost**: $0 (no real resources created)
- **Duration**: Instant preview
- **Trigger**: Every PR automatically
- **Action**: `pulumi preview` only

### Dev Environments (Local Only)
- **Purpose**: Local development iteration and testing
- **Cost**: Real cloud charges (minimized tiers)
- **Duration**: Persistent until manually destroyed
- **Trigger**: Developer runs `pulumi up` locally
- **Action**: `pulumi up` (provisions real resources)

## Setup

1. **Install dependencies**:
   ```bash
   cd infra
   uv sync
   ```

2. **For Local Development**:
   ```bash
   # Set up a local dev stack
   pulumi stack init dev
   pulumi config set aws:region us-west-1
   pulumi config set infra:environment dev
   pulumi config set infra:client_base_url http://localhost:3000
   pulumi config set infra:server_base_url http://localhost:8080
   
   # Deploy real resources for development
   pulumi up
   ```

3. **For Preview Only**:
   ```bash
   # Preview changes without deploying
   pulumi preview
   ```

## Architecture

The infrastructure creates the following AWS resources:

- **VPC** with public subnet for ECS tasks
- **ECS Fargate Cluster** for running containers
- **ECR Repository** for storing Docker images
- **ECS Service** with task definition
- **IAM Roles** for ECS task execution
- **CloudWatch Log Group** for application logs
- **Security Groups** for network access control

## Deployment

### Preview Environments (Automatic)

Every PR automatically triggers a preview environment that:
- Runs `pulumi preview` to show infrastructure changes
- Costs $0 (no real resources created)
- Provides instant feedback on infrastructure changes
- Automatically cleans up when PR is closed

### Dev Environments (Local Only)

For actual deployments with real resources, developers use Pulumi CLI locally:

```bash
# Set up a local dev stack
pulumi stack init dev
pulumi config set aws:region us-west-1
pulumi config set infra:environment dev
pulumi config set infra:client_base_url http://localhost:3000
pulumi config set infra:server_base_url http://localhost:8080

# Deploy real resources for development
pulumi up

# When done developing, destroy resources
pulumi destroy
```

### Workflow Files
- `.github/workflows/preview.yml` - PR preview environments (ephemeral)

## Environment Variables

The server application expects the following environment variables:

- `ENVIRONMENT`: Current environment (dev, staging, prod)
- `CLIENT_BASE_URL`: Frontend base URL
- `SERVER_BASE_URL`: Server base URL
- `AWS_REGION`: AWS region (defaults to us-west-1)
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `COGNITO_CLIENT_ID`: Cognito App Client ID
- `COGNITO_CLIENT_SECRET`: Cognito App Client Secret (if required)
- `COGNITO_DOMAIN`: Cognito domain URL

## Monitoring

- **ECS Service**: Monitor service health and task status
- **CloudWatch Logs**: Application logs are sent to `/ecs/maive-server-{environment}`
- **ECR Repository**: Container images are stored in `maive-server-{environment}`

## Scaling

The current setup runs 1 task instance. To scale:

1. Update the `desired_count` in the ECS service
2. Consider adding an Application Load Balancer for production
3. Implement auto-scaling policies based on CPU/memory usage

## Security

- ECS tasks run in a public subnet with security groups
- IAM roles follow least privilege principle
- ECR repository has image scanning enabled
- All resources are tagged with environment for cost tracking

## Cost Optimization

- Use Fargate Spot for non-production workloads
- Set appropriate CPU/memory limits
- Monitor CloudWatch metrics for resource utilization
- Clean up unused ECR images periodically