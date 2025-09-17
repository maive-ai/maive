"""AWS Infrastructure for Maive application using Pulumi"""

import pulumi
import pulumi_docker_build as docker_build
from pulumi import FileArchive
from pulumi_aws import (
    acm,
    apigatewayv2,
    cloudwatch,
    cognito,
    dynamodb,
    ec2,
    ecr,
    ecs,
    iam,
    lambda_,
    lb,
    route53,
    s3,
    sfn,
)

# Configuration
config = pulumi.Config()
aws_cfg = pulumi.Config("aws")
s3_cfg = pulumi.Config("s3")
gemini_cfg = pulumi.Config("google_genai")
pulse_ai_cfg = pulumi.Config("pulse_ai")
vapi_cfg = pulumi.Config("vapi")
voice_ai_cfg = pulumi.Config("voice_ai")
email_cfg = pulumi.Config("email")
# Get stack name for dynamic resource naming
stack_name = pulumi.get_stack()
environment = config.require("environment")

certificate_domain = config.require("certificate_domain")
deploy_containers = config.require_bool("deploy_containers")
force_destroy_buckets = s3_cfg.get_bool("force_destroy") or False

app_name = "maive"
server_app_name = f"{app_name}-server"
web_app_name = f"{app_name}-web"

# Construct the Cognito domain URL
cognito_domain_url = pulumi.Output.format(
    "https://{}-maive.auth-fips.us-gov-west-1.amazoncognito.com",
    stack_name,
)

app_domain_url = pulumi.Output.format(
    "{}://{}",
    config.require("transport_protocol"),
    certificate_domain,
)
pulumi.export("app_domain_url", app_domain_url)

# Construct the OAuth redirect URI
oauth_redirect_uri = pulumi.Output.format(
    "{}/{}",
    app_domain_url,
    config.require("oauth_redirect_route").lstrip("/"),
)

pulumi.log.info(
    f"Launching {app_name} in {environment} Pulumi environment at {certificate_domain}!"
)

# VPC and Networking
vpc = ec2.Vpc(
    f"{app_name}-vpc-{stack_name}",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={
        "Name": f"{app_name}-vpc-{environment}",
        "Environment": environment,
    },
)

# Internet Gateway
internet_gateway = ec2.InternetGateway(
    f"{app_name}-igw-{stack_name}",
    vpc_id=vpc.id,
    tags={
        "Name": f"{app_name}-igw-{environment}",
        "Environment": environment,
    },
)

# Public Subnet 1
public_subnet_1 = ec2.Subnet(
    f"{app_name}-public-subnet-1-{stack_name}",
    vpc_id=vpc.id,
    cidr_block="10.0.3.0/24",
    availability_zone="us-gov-west-1a",
    map_public_ip_on_launch=True,
    tags={
        "Name": f"{app_name}-public-subnet-1-{environment}",
        "Environment": environment,
    },
)

# Public Subnet 2
public_subnet_2 = ec2.Subnet(
    f"{app_name}-public-subnet-2-{stack_name}",
    vpc_id=vpc.id,
    cidr_block="10.0.4.0/24",
    availability_zone="us-gov-west-1b",
    map_public_ip_on_launch=True,
    tags={
        "Name": f"{app_name}-public-subnet-2-{environment}",
        "Environment": environment,
    },
)

# Route Table for Public Subnet
public_route_table = ec2.RouteTable(
    f"{app_name}-public-rt-{stack_name}",
    vpc_id=vpc.id,
    routes=[
        ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=internet_gateway.id,
        )
    ],
    tags={
        "Name": f"{app_name}-public-rt-{environment}",
        "Environment": environment,
    },
)

# Route Table Association for Subnet 1
public_route_table_association_1 = ec2.RouteTableAssociation(
    f"{app_name}-public-rta-1-{stack_name}",
    subnet_id=public_subnet_1.id,
    route_table_id=public_route_table.id,
)

# # Route Table Association for Subnet 2
public_route_table_association_2 = ec2.RouteTableAssociation(
    f"{app_name}-public-rta-2-{stack_name}",
    subnet_id=public_subnet_2.id,
    route_table_id=public_route_table.id,
)

# Security Group for ALB
alb_security_group = ec2.SecurityGroup(
    f"{app_name}-alb-sg-{stack_name}",
    description="Security group for Application Load Balancer",
    vpc_id=vpc.id,
    ingress=[
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow HTTP traffic to ALB",
        ),
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow HTTPS traffic to ALB",
        ),
    ],
    egress=[
        ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow all outbound traffic",
        )
    ],
    tags={
        "Name": f"{app_name}-alb-sg-{environment}",
        "Environment": environment,
    },
)

# Security Group for ECS Tasks
ecs_security_group = ec2.SecurityGroup(
    f"{server_app_name}-ecs-sg-{stack_name}",
    description="Security group for ECS tasks",
    vpc_id=vpc.id,
    ingress=[
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=8080,
            to_port=8080,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow HTTP traffic to FastAPI server",
        )
    ],
    egress=[
        ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow all outbound traffic",
        )
    ],
    tags={
        "Name": f"{server_app_name}-ecs-sg-{environment}",
        "Environment": environment,
    },
)

# Security Group for Web App (Nginx)
web_security_group = ec2.SecurityGroup(
    f"{web_app_name}-sg-{stack_name}",
    description="Security group for web app (Nginx)",
    vpc_id=vpc.id,
    ingress=[
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow HTTP traffic to web app (Nginx)",
        )
    ],
    egress=[
        ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow all outbound traffic",
        )
    ],
    tags={
        "Name": f"{web_app_name}-sg-{environment}",
        "Environment": environment,
    },
)

# ECS Cluster
cluster = ecs.Cluster(
    f"{app_name}-cluster-{stack_name}",
    name=f"{app_name}-{stack_name}",
    settings=[
        ecs.ClusterSettingArgs(
            name="containerInsights",
            value="enabled",
        )
    ],
    tags={
        "Name": f"{app_name}-cluster",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Task Execution Role
task_execution_role = iam.Role(
    f"{app_name}-task-execution-role-{stack_name}",
    assume_role_policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                }
            ],
        }
    ),
    managed_policy_arns=[
        "arn:aws-us-gov:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
    ],
    tags={
        "Name": f"{app_name}-task-execution-role-{environment}",
        "Environment": environment,
    },
)

# Task Role (for application permissions)
task_role = iam.Role(
    f"{app_name}-task-role-{stack_name}",
    assume_role_policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                }
            ],
        }
    ),
    tags={
        "Name": f"{app_name}-task-role-{environment}",
        "Environment": environment,
    },
)

# CloudWatch Log Group
log_group = cloudwatch.LogGroup(
    f"{app_name}-logs-{stack_name}",
    name=f"/ecs/{app_name}-{stack_name}",
    retention_in_days=90,
    tags={
        "Name": f"{app_name}-logs",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# ECR Repository (conditional)
ecr_repository = None
if deploy_containers:
    ecr_repository = ecr.Repository(
        f"{server_app_name}-repo-{stack_name}",
        name=f"{server_app_name}-{stack_name}",
        image_scanning_configuration=ecr.RepositoryImageScanningConfigurationArgs(
            scan_on_push=True,
        ),
        tags={
            "Name": f"{server_app_name}-repo",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# ECR Repository for Web App (conditional)
web_ecr_repository = None
if deploy_containers:
    web_ecr_repository = ecr.Repository(
        f"{web_app_name}-repo-{stack_name}",
        name=f"{web_app_name}-{stack_name}",
        image_scanning_configuration=ecr.RepositoryImageScanningConfigurationArgs(
            scan_on_push=True,
        ),
        tags={
            "Name": f"{web_app_name}-repo",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# Get ECR authorization token for pushing images (conditional)
auth_token = None
server_image = None
if deploy_containers:
    auth_token = ecr.get_authorization_token_output(
        registry_id=ecr_repository.registry_id
    )

    # Build and push server Docker image
    server_image = docker_build.Image(
        f"{server_app_name}-image",
        context=docker_build.BuildContextArgs(
            location="../",  # Monorepo root
        ),
        dockerfile=docker_build.DockerfileArgs(
            location="../apps/server/Dockerfile",
        ),
        platforms=["linux/amd64"],  # Ensure compatibility with AWS Fargate
        tags=[ecr_repository.repository_url.apply(lambda url: f"{url}:latest")],
        push=True,
        registries=[
            docker_build.RegistryArgs(
                address=ecr_repository.repository_url,
                username=auth_token.user_name,
                password=pulumi.Output.secret(auth_token.password),
            )
        ],
    )


# Target Group for ECS Tasks (conditional)
target_group = None
if deploy_containers:
    target_group = lb.TargetGroup(
        f"{server_app_name}-tg-{stack_name}",
        name=f"{server_app_name}-{stack_name}",
        port=8080,
        protocol="HTTP",
        target_type="ip",
        vpc_id=vpc.id,
        health_check=lb.TargetGroupHealthCheckArgs(
            enabled=True,
            healthy_threshold=2,
            interval=30,
            matcher="200",
            path="/healthcheck",
            port="traffic-port",
            protocol="HTTP",
            timeout=5,
            unhealthy_threshold=2,
        ),
        tags={
            "Name": f"{server_app_name}-tg",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# Target Group for Web App (conditional)
web_target_group = None
if deploy_containers:
    web_target_group = lb.TargetGroup(
        f"{web_app_name}-tg-{stack_name}",
        name=f"{web_app_name}-{stack_name}",
        port=80,
        protocol="HTTP",
        vpc_id=vpc.id,
        target_type="ip",
        health_check=lb.TargetGroupHealthCheckArgs(
            path="/healthcheck",
            protocol="HTTP",
            matcher="200",
            interval=30,
            timeout=5,
            healthy_threshold=2,
            unhealthy_threshold=2,
        ),
        tags={
            "Name": f"{web_app_name}-tg",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# Application Load Balancer (conditional)
alb = None
if deploy_containers:
    alb = lb.LoadBalancer(
        f"{app_name}-alb-{stack_name}",
        name=f"{app_name}-{stack_name}",
        internal=False,
        load_balancer_type="application",
        security_groups=[alb_security_group.id],
        subnets=[public_subnet_1.id, public_subnet_2.id],
        enable_deletion_protection=False,
        tags={
            "Name": f"{app_name}-alb",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# SSL Certificate for ALB (conditional)
ssl_certificate = None
if deploy_containers:
    ssl_certificate = acm.Certificate(
        f"{app_name}-ssl-cert-{stack_name}",
        domain_name=certificate_domain,
        validation_method="DNS",
        tags={
            "Name": f"{app_name}-ssl-cert",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# DNS Validation Records (conditional)
zone = None
validation_records = None
if deploy_containers:
    zone = route53.Zone(
        f"{app_name}-zone-{stack_name}",
        name=certificate_domain,
        tags={
            "Name": f"{app_name}-zone",
            "Environment": environment,
            "Stack": stack_name,
        },
    )
    validation_records = ssl_certificate.domain_validation_options.apply(
        lambda opts: [
            route53.Record(
                f"{app_name}-cert-validate-{i}-{stack_name}",
                name=o.resource_record_name,
                records=[o.resource_record_value],
                ttl=60,
                type=o.resource_record_type,
                zone_id=zone.zone_id,
                allow_overwrite=True,
            )
            for i, o in enumerate(opts)
        ]
    )

# Certificate Validation (conditional)
certificate_validation = None
if deploy_containers:
    certificate_validation = acm.CertificateValidation(
        f"{app_name}-cert-validation-{stack_name}",
        certificate_arn=ssl_certificate.arn,
        validation_record_fqdns=validation_records.apply(
            lambda recs: [r.fqdn for r in recs]
        ),
    )

# Create DNS alias record for the application domain (conditional)
app_alias_record = None
if deploy_containers:
    app_alias_record = route53.Record(
        f"{app_name}-alias-record-{stack_name}",
        name=certificate_domain,
        type="A",
        zone_id=zone.zone_id,
        aliases=[
            route53.RecordAliasArgs(
                name=alb.dns_name,
                zone_id=alb.zone_id,
                evaluate_target_health=True,
            )
        ],
    )

# ALB Listeners (conditional)
listener = None
https_listener = None
if deploy_containers:
    # ALB Listener (now redirects to HTTPS)
    listener = lb.Listener(
        f"{app_name}-listener-{stack_name}",
        load_balancer_arn=alb.arn,
        port=80,
        protocol="HTTP",
        default_actions=[
            lb.ListenerDefaultActionArgs(
                type="redirect",
                redirect=lb.ListenerDefaultActionRedirectArgs(
                    port="443",
                    protocol="HTTPS",
                    status_code="HTTP_301",
                ),
            )
        ],
    )

    # ALB HTTPS Listener
    https_listener = lb.Listener(
        f"{app_name}-https-listener-{stack_name}",
        load_balancer_arn=alb.arn,
        port=443,
        protocol="HTTPS",
        ssl_policy="ELBSecurityPolicy-TLS-1-2-2017-01",
        certificate_arn=ssl_certificate.arn,
        default_actions=[
            lb.ListenerDefaultActionArgs(
                type="forward",
                target_group_arn=web_target_group.arn,  # Default to web app
            )
        ],
        opts=pulumi.ResourceOptions(depends_on=[certificate_validation]),
    )

# Listener Rule for API traffic (conditional)
alb_listener_rule_api = None
if deploy_containers:
    alb_listener_rule_api = lb.ListenerRule(
        f"{server_app_name}-api-rule-{stack_name}",
        listener_arn=https_listener.arn,
        priority=10,  # Lower number means higher priority
        actions=[
            lb.ListenerRuleActionArgs(
                type="forward",
                target_group_arn=target_group.arn,
            )
        ],
        conditions=[
            lb.ListenerRuleConditionArgs(
                path_pattern=lb.ListenerRuleConditionPathPatternArgs(
                    values=["/api/*"],
                ),
            )
        ],
        opts=pulumi.ResourceOptions(parent=https_listener),
    )

# Add Cognito configuration
cognito_config = pulumi.Config("cognito")

# Create a new Cognito User Pool with the same settings as your GUI pool
user_pool = cognito.UserPool(
    f"{app_name}-user-pool-{stack_name}",
    name=stack_name,
    password_policy=cognito.UserPoolPasswordPolicyArgs(
        minimum_length=8,
        require_uppercase=True,
        require_lowercase=True,
        require_numbers=True,
        require_symbols=True,
        temporary_password_validity_days=7,
    ),
    mfa_configuration="ON",
    software_token_mfa_configuration=cognito.UserPoolSoftwareTokenMfaConfigurationArgs(
        enabled=True,
    ),
    username_attributes=["email"],
    auto_verified_attributes=["email"],
    lambda_config={},
    verification_message_template=cognito.UserPoolVerificationMessageTemplateArgs(
        default_email_option="CONFIRM_WITH_CODE",
    ),
    account_recovery_setting=cognito.UserPoolAccountRecoverySettingArgs(
        recovery_mechanisms=[
            cognito.UserPoolAccountRecoverySettingRecoveryMechanismArgs(
                name="verified_email", priority=1
            ),
            cognito.UserPoolAccountRecoverySettingRecoveryMechanismArgs(
                name="verified_phone_number", priority=2
            ),
        ],
    ),
    email_configuration=cognito.UserPoolEmailConfigurationArgs(
        email_sending_account="COGNITO_DEFAULT",
    ),
    admin_create_user_config=cognito.UserPoolAdminCreateUserConfigArgs(
        allow_admin_create_user_only=cognito_config.require_bool(
            "allow_admin_create_user_only"
        ),
    ),
    username_configuration=cognito.UserPoolUsernameConfigurationArgs(
        case_sensitive=False,
    ),
)

# Create a new Cognito User Pool Client mirroring your GUI client
pool_client = cognito.UserPoolClient(
    f"{app_name}-user-pool-client-{stack_name}",
    user_pool_id=user_pool.id,
    name=cognito_config.require("client_name"),
    generate_secret=True,
    access_token_validity=60,
    id_token_validity=60,
    refresh_token_validity=7,
    token_validity_units=cognito.UserPoolClientTokenValidityUnitsArgs(
        access_token="minutes",
        id_token="minutes",
        refresh_token="days",
    ),
    explicit_auth_flows=["ALLOW_USER_AUTH", "ALLOW_USER_SRP_AUTH"],
    supported_identity_providers=["COGNITO"],
    callback_urls=cognito_config.require_object("callback_urls"),
    allowed_oauth_flows=["code"],
    allowed_oauth_scopes=["email", "openid", "profile"],
    allowed_oauth_flows_user_pool_client=True,
    enable_token_revocation=True,
    enable_propagate_additional_user_context_data=False,
    auth_session_validity=15,
    refresh_token_rotation=cognito.UserPoolClientRefreshTokenRotationArgs(
        feature="ENABLED",
        retry_grace_period_seconds=60,
    ),
    prevent_user_existence_errors="ENABLED",
)

# Create Cognito User Pool Domain for the managed login page
user_pool_domain = cognito.UserPoolDomain(
    f"{app_name}-user-pool-domain-{stack_name}",
    domain=f"{stack_name}-maive",
    user_pool_id=user_pool.id,
    managed_login_version=2,
)

# S3 bucket for PDF uploads
upload_bucket = s3.Bucket(
    f"{app_name}-upload-bucket-{stack_name}",
    bucket=f"{app_name}-upload-bucket-{stack_name}",
    force_destroy=force_destroy_buckets,
    cors_rules=[
        s3.BucketCorsRuleArgs(
            allowed_headers=["*"],
            allowed_methods=["PUT", "POST", "GET"],
            allowed_origins=[
                app_domain_url,
                "http://localhost:3000",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8080",
            ],
            expose_headers=["ETag"],
            max_age_seconds=3000,
        )
    ],
    tags={
        "Name": f"{app_name}-upload-bucket-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# S3 bucket for email content storage
email_content_bucket = s3.Bucket(
    f"{app_name}-email-content-bucket-{stack_name}",
    bucket=f"{app_name}-email-content-{stack_name}",
    force_destroy=force_destroy_buckets,
    tags={
        "Name": f"{app_name}-email-content-bucket-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# DynamoDB table for email processing jobs
email_processing_table = dynamodb.Table(
    f"{app_name}-email-processing-table",
    name=f"{app_name}-email-processing-table-{stack_name}",
    attributes=[
        dynamodb.TableAttributeArgs(name="email_id", type="S"),
        dynamodb.TableAttributeArgs(name="received_at", type="S"),
        dynamodb.TableAttributeArgs(name="platform", type="S"),
    ],
    hash_key="email_id",
    range_key="received_at",
    global_secondary_indexes=[
        dynamodb.TableGlobalSecondaryIndexArgs(
            name="platform-emails-index",
            hash_key="platform",
            range_key="received_at",
            projection_type="ALL",
        )
    ],
    billing_mode="PAY_PER_REQUEST",
    tags={
        "Name": f"{app_name}-email-processing-table-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# DynamoDB table for upload trace
upload_table = dynamodb.Table(
    f"{app_name}-upload-table",
    name=f"{app_name}-upload-table-{stack_name}",
    attributes=[
        dynamodb.TableAttributeArgs(name="user_email", type="S"),
        dynamodb.TableAttributeArgs(name="timestamp", type="S"),
    ],
    hash_key="user_email",
    range_key="timestamp",
    billing_mode="PAY_PER_REQUEST",
    tags={
        "Name": f"{app_name}-upload-table-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# DynamoDB table for AI processing jobs
jobs_table = dynamodb.Table(
    f"{app_name}-jobs-table",
    name=f"{app_name}-jobs-table-{stack_name}",
    attributes=[
        dynamodb.TableAttributeArgs(name="job_id", type="S"),
        dynamodb.TableAttributeArgs(name="user_email", type="S"),
        dynamodb.TableAttributeArgs(name="created_at", type="S"),
    ],
    hash_key="job_id",
    global_secondary_indexes=[
        dynamodb.TableGlobalSecondaryIndexArgs(
            name="user-jobs-index",
            hash_key="user_email",
            range_key="created_at",
            projection_type="ALL",
        )
    ],
    billing_mode="PAY_PER_REQUEST",
    tags={
        "Name": f"{app_name}-jobs-table-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# DynamoDB table for workflows
workflows_table = dynamodb.Table(
    f"{app_name}-workflows-table",
    name=f"{app_name}-workflows-table-{stack_name}",
    attributes=[
        dynamodb.TableAttributeArgs(name="PK", type="S"),  # USER#{user_email}
        dynamodb.TableAttributeArgs(name="SK", type="S"),  # WORKFLOW#{workflow_id}
    ],
    hash_key="PK",
    range_key="SK",
    billing_mode="PAY_PER_REQUEST",
    tags={
        "Name": f"{app_name}-workflows-table-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# DynamoDB table for template schemas
template_schemas_table = dynamodb.Table(
    f"{app_name}-template-schemas-table",
    name=f"{app_name}-template-schemas-table-{stack_name}",
    attributes=[
        dynamodb.TableAttributeArgs(name="user_email", type="S"),
        dynamodb.TableAttributeArgs(name="workflow_id", type="S"),
    ],
    hash_key="user_email",
    range_key="workflow_id",
    billing_mode="PAY_PER_REQUEST",
    tags={
        "Name": f"{app_name}-template-schemas-table-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# DynamoDB table for customer CRM data (mock)
customers_table = dynamodb.Table(
    f"{app_name}-customers-table",
    name=f"{app_name}-customers-table-{stack_name}",
    attributes=[
        dynamodb.TableAttributeArgs(name="customer_id", type="S"),
        dynamodb.TableAttributeArgs(name="crm_source", type="S"),
        dynamodb.TableAttributeArgs(name="homeowner_name_lower", type="S"),
        dynamodb.TableAttributeArgs(name="updated_at", type="S"),
    ],
    hash_key="customer_id",
    global_secondary_indexes=[
        dynamodb.TableGlobalSecondaryIndexArgs(
            name="crm-customers-index",
            hash_key="crm_source",
            range_key="homeowner_name_lower",
            projection_type="ALL",
        ),
        dynamodb.TableGlobalSecondaryIndexArgs(
            name="recent-updates-index",
            hash_key="crm_source",
            range_key="updated_at",
            projection_type="ALL",
        ),
    ],
    billing_mode="PAY_PER_REQUEST",
    tags={
        "Name": f"{app_name}-customers-table-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# DynamoDB table for photo analysis jobs
photo_analysis_table = dynamodb.Table(
    f"{app_name}-photo-analysis-table",
    name=f"{app_name}-photo-analysis-table-{stack_name}",
    attributes=[
        dynamodb.TableAttributeArgs(name="job_id", type="S"),
        dynamodb.TableAttributeArgs(name="user_email", type="S"),
        dynamodb.TableAttributeArgs(name="created_at", type="S"),
    ],
    hash_key="job_id",
    global_secondary_indexes=[
        dynamodb.TableGlobalSecondaryIndexArgs(
            name="user-photos-index",
            hash_key="user_email",
            range_key="created_at",
            projection_type="ALL",
        )
    ],
    billing_mode="PAY_PER_REQUEST",
    tags={
        "Name": f"{app_name}-photo-analysis-table-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# IAM role for Lambda functions (updated with email processing permissions)
upload_lambda_role = iam.Role(
    f"{app_name}-upload-lambda-role-{stack_name}",
    assume_role_policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                }
            ],
        }
    ),
    tags={
        "Name": f"{app_name}-upload-lambda-role-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Inline policy for S3 and DynamoDB access (including email processing table)
upload_lambda_policy = iam.RolePolicy(
    f"{app_name}-upload-lambda-policy",
    role=upload_lambda_role.id,
    policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:PutObject", "s3:GetObject"],
                    "Resource": [
                        upload_bucket.arn.apply(lambda arn: f"{arn}/*"),
                        email_content_bucket.arn.apply(lambda arn: f"{arn}/*"),
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": ["dynamodb:PutItem"],
                    "Resource": [upload_table.arn],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:Query",
                    ],
                    "Resource": [
                        jobs_table.arn,
                        jobs_table.arn.apply(lambda arn: f"{arn}/index/*"),
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                    ],
                    "Resource": [workflows_table.arn],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                    ],
                    "Resource": [template_schemas_table.arn],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                    ],
                    "Resource": [
                        customers_table.arn,
                        customers_table.arn.apply(lambda arn: f"{arn}/index/*"),
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                    ],
                    "Resource": [
                        email_processing_table.arn,
                        email_processing_table.arn.apply(lambda arn: f"{arn}/index/*"),
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                    ],
                    "Resource": [
                        photo_analysis_table.arn,
                        photo_analysis_table.arn.apply(lambda arn: f"{arn}/index/*"),
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "states:StartExecution",
                        "states:DescribeExecution",
                    ],
                    "Resource": [
                        workflows_table.arn,
                        template_schemas_table.arn,
                        upload_table.arn,
                        email_processing_table.arn,
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    "Resource": ["arn:aws-us-gov:logs:*:*:*"],
                },
            ],
        }
    ),
)

# IAM role for Step Functions
step_functions_role = iam.Role(
    f"{app_name}-step-functions-role-{stack_name}",
    assume_role_policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "states.amazonaws.com"},
                }
            ],
        }
    ),
    tags={
        "Name": f"{app_name}-step-functions-role-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Step Functions policy to invoke Lambda and write to DynamoDB
step_functions_policy = iam.RolePolicy(
    f"{app_name}-step-functions-policy",
    role=step_functions_role.id,
    policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["lambda:InvokeFunction"],
                    "Resource": ["*"],  # Will be restricted to specific Lambdas
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                    ],
                    "Resource": [
                        jobs_table.arn,
                        email_processing_table.arn,
                        photo_analysis_table.arn,
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                    ],
                    "Resource": [template_schemas_table.arn, customers_table.arn],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:CreateLogDelivery",
                        "logs:GetLogDelivery",
                        "logs:UpdateLogDelivery",
                        "logs:DeleteLogDelivery",
                        "logs:ListLogDeliveries",
                        "logs:PutResourcePolicy",
                        "logs:DescribeResourcePolicies",
                        "logs:DescribeLogGroups",
                    ],
                    "Resource": ["*"],
                },
            ],
        }
    ),
)

# Lambda to generate pre-signed URL
get_upload_url_lambda = lambda_.Function(
    f"{app_name}-get-upload-url-{stack_name}",
    runtime="python3.13",
    handler="get_presigned_url.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/get_presigned_url/lambda_function.zip"),
    role=upload_lambda_role.arn,
    timeout=10,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "BUCKET_NAME": upload_bucket.bucket,
        }
    ),
    tags={
        "Name": f"{app_name}-get-upload-url-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to record metadata in DynamoDB
create_upload_record_lambda = lambda_.Function(
    f"{app_name}-create-upload-record-{stack_name}",
    runtime="python3.13",
    handler="create_record.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/create_record/lambda_function.zip"),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "TABLE_NAME": upload_table.name,
        }
    ),
    tags={
        "Name": f"{app_name}-create-upload-record-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to query Gemini AI
query_gemini_ai_lambda = lambda_.Function(
    f"{app_name}-query-gemini-ai-{stack_name}",
    runtime="python3.13",
    handler="query_gemini_ai.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/query_gemini_ai/lambda_function.zip"),
    role=upload_lambda_role.arn,
    timeout=config.get_int("lambda_timeout_seconds") or 900,
    memory_size=512,
    layers=[
        "arn:aws-us-gov:lambda:us-gov-west-1:416450511684:layer:pandasPython3_13:1"
    ],
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "GEMINI_AI_TEMPLATE_SCHEMAS_TABLE_NAME": template_schemas_table.name,
            "GEMINI_AI_JOBS_TABLE_NAME": jobs_table.name,
            "GEMINI_AI_S3_BUCKET_NAME": upload_bucket.bucket,
            "GEMINI_AI_EMAIL_S3_BUCKET_NAME": email_content_bucket.bucket,
            "GEMINI_AI_GEMINI_API_KEY": config.require_secret("gemini_api_key"),
            "GEMINI_AI_MODEL_NAME": gemini_cfg.require("model_name"),
            "GEMINI_AI_TEMPERATURE": gemini_cfg.require("temperature"),
            "GEMINI_AI_TOP_P": gemini_cfg.require("top_p"),
            "GEMINI_AI_TOP_K": gemini_cfg.require("top_k"),
            "GEMINI_AI_THINKING_BUDGET": gemini_cfg.require("thinking_budget"),
            "GEMINI_AI_ENABLE_LOW_CONFIDENCE_FLAGGING": gemini_cfg.require(
                "enable_low_confidence_flagging"
            ),
            "GEMINI_AI_SYSTEM_INSTRUCTIONS": gemini_cfg.require("system_instructions"),
        }
    ),
    tags={
        "Name": f"{app_name}-query-gemini-ai-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to query Pulse AI
query_pulse_ai_lambda = lambda_.Function(
    f"{app_name}-query-pulse-ai-{stack_name}",
    runtime="python3.13",
    handler="query_pulse_ai.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/query_pulse_ai/lambda_function.zip"),
    role=upload_lambda_role.arn,
    timeout=config.get_int("lambda_timeout_seconds") or 900,
    memory_size=512,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "PULSE_AI_S3_BUCKET_NAME": upload_bucket.bucket,
            "PULSE_AI_PULSE_API_KEY": pulse_ai_cfg.require_secret("api_key"),
            "PULSE_AI_PULSE_BASE_URL": pulse_ai_cfg.require("base_url"),
        }
    ),
    tags={
        "Name": f"{app_name}-query-pulse-ai-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)


process_template_lambda = lambda_.Function(
    f"{app_name}-process-template-{stack_name}",
    runtime="python3.13",
    handler="process_template.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/process_template/lambda_function.zip"),
    role=upload_lambda_role.arn,
    layers=[
        "arn:aws-us-gov:lambda:us-gov-west-1:416450511684:layer:pandasPython3_13:1"
    ],
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "TEMPLATE_SCHEMAS_TABLE_NAME": template_schemas_table.name,
            "TEMPLATE_BUCKET_NAME": upload_bucket.bucket,
        }
    ),
    tags={
        "Name": f"{app_name}-process-template-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)


# Step Functions State Machine for AI processing
ai_processing_state_machine = sfn.StateMachine(
    f"{app_name}-ai-processing-state-machine-{stack_name}",
    name=f"{app_name}-ai-processing-{stack_name}",
    role_arn=step_functions_role.arn,
    definition=pulumi.Output.json_dumps(
        {
            "Comment": "AI processing workflow with Pulse AI and Gemini AI",
            "StartAt": "UpdateJobStatus",
            "States": {
                "UpdateJobStatus": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:updateItem",
                    "Parameters": {
                        "TableName": jobs_table.name,
                        "Key": {"job_id": {"S.$": "$.job_id"}},
                        "UpdateExpression": "SET job_status = :status, started_at = :started_at",
                        "ExpressionAttributeValues": {
                            ":status": {"S": "PROCESSING"},
                            ":started_at": {"S.$": "$$.State.EnteredTime"},
                        },
                    },
                    "ResultPath": "$.updateResult",
                    "Next": "ExtractWithPulseAI",
                    "Catch": [
                        {"ErrorEquals": ["States.TaskFailed"], "Next": "HandleFailure"}
                    ],
                },
                "ExtractWithPulseAI": {
                    "Type": "Task",
                    "Resource": query_pulse_ai_lambda.arn,
                    "Parameters": {
                        "s3_key.$": "$.s3_key",
                    },
                    "ResultPath": "$.pulseResult",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0,
                        }
                    ],
                    "Next": "GetTemplateSchema",
                    "Catch": [
                        {"ErrorEquals": ["States.TaskFailed"], "Next": "HandleFailure"}
                    ],
                },
                "GetTemplateSchema": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:getItem",
                    "Parameters": {
                        "TableName": template_schemas_table.name,
                        "Key": {
                            "user_email": {"S.$": "$.user_email"},
                            "workflow_id": {"S.$": "$.workflow_id"},
                        },
                    },
                    "ResultPath": "$.templateResult",
                    "Next": "CheckTemplateExists",
                    "Catch": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "Next": "ProcessWithGeminiAIWithoutTemplate",
                        }
                    ],
                },
                "CheckTemplateExists": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.templateResult.Item",
                            "IsPresent": True,
                            "Next": "ProcessWithGeminiAIWithTemplate",
                        }
                    ],
                    "Default": "ProcessWithGeminiAIWithoutTemplate",
                },
                "ProcessWithGeminiAIWithTemplate": {
                    "Type": "Task",
                    "Resource": query_gemini_ai_lambda.arn,
                    "Parameters": {
                        "s3_key.$": "$.s3_key",
                        "prompt.$": "$.prompt",
                        "json_schema.$": "$.templateResult.Item.json_schema.S",
                        "doc_extract_data.$": "$.pulseResult.body",
                    },
                    "ResultPath": "$.lambdaResult",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0,
                        }
                    ],
                    "Next": "SaveResult",
                    "Catch": [
                        {"ErrorEquals": ["States.TaskFailed"], "Next": "HandleFailure"}
                    ],
                },
                "ProcessWithGeminiAIWithoutTemplate": {
                    "Type": "Task",
                    "Resource": query_gemini_ai_lambda.arn,
                    "Parameters": {
                        "s3_key.$": "$.s3_key",
                        "prompt.$": "$.prompt",
                        "doc_extract_data.$": "$.pulseResult.body",
                    },
                    "ResultPath": "$.lambdaResult",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0,
                        }
                    ],
                    "Next": "SaveResult",
                    "Catch": [
                        {"ErrorEquals": ["States.TaskFailed"], "Next": "HandleFailure"}
                    ],
                },
                "SaveResult": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:updateItem",
                    "Parameters": {
                        "TableName": jobs_table.name,
                        "Key": {"job_id": {"S.$": "$.job_id"}},
                        "UpdateExpression": "SET job_status = :status, completed_at = :completed_at, #result = :result",
                        "ExpressionAttributeNames": {"#result": "result"},
                        "ExpressionAttributeValues": {
                            ":status": {"S": "COMPLETED"},
                            ":completed_at": {"S.$": "$$.State.EnteredTime"},
                            ":result": {"S.$": "$.lambdaResult.body"},
                        },
                    },
                    "End": True,
                },
                "HandleFailure": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:updateItem",
                    "Parameters": {
                        "TableName": jobs_table.name,
                        "Key": {"job_id": {"S.$": "$.job_id"}},
                        "UpdateExpression": "SET job_status = :status, completed_at = :completed_at, error_message = :error",
                        "ExpressionAttributeValues": {
                            ":status": {"S": "FAILED"},
                            ":completed_at": {"S.$": "$$.State.EnteredTime"},
                            ":error": {"S.$": "$.Error"},
                        },
                    },
                    "End": True,
                },
            },
        }
    ),
    tags={
        "Name": f"{app_name}-ai-processing-state-machine-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to update customers from email processing data
update_customer_from_email_lambda = lambda_.Function(
    f"{app_name}-update-customer-from-email-{stack_name}",
    runtime="python3.13",
    handler="update_customer_from_email.handler.lambda_handler",
    code=FileArchive(
        "../apps/backend/functions/update_customer_from_email/lambda_function.zip"
    ),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "UPDATE_CUSTOMER_CUSTOMERS_TABLE_NAME": customers_table.name,
            "UPDATE_CUSTOMER_AWS_REGION": aws_cfg.require("region"),
        }
    ),
    tags={
        "Name": f"{app_name}-update-customer-from-email-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Step Functions State Machine for Email Processing
email_processing_state_machine = sfn.StateMachine(
    f"{app_name}-email-processing-state-machine-{stack_name}",
    name=f"{app_name}-email-processing-{stack_name}",
    role_arn=step_functions_role.arn,
    definition=pulumi.Output.json_dumps(
        {
            "Comment": "Email processing workflow with Gemini AI",
            "StartAt": "UpdateEmailJobStatus",
            "States": {
                "UpdateEmailJobStatus": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:updateItem",
                    "Parameters": {
                        "TableName": email_processing_table.name,
                        "Key": {
                            "email_id": {"S.$": "$.email_id"},
                            "received_at": {"S.$": "$.email_metadata.received_at"},
                        },
                        "UpdateExpression": "SET #status = :status, started_at = :started_at, updated_at = :updated_at",
                        "ExpressionAttributeNames": {"#status": "status"},
                        "ExpressionAttributeValues": {
                            ":status": {"S": "PROCESSING"},
                            ":started_at": {"S.$": "$$.State.EnteredTime"},
                            ":updated_at": {"S.$": "$$.State.EnteredTime"},
                        },
                    },
                    "ResultPath": "$.updateResult",
                    "Next": "ProcessWithGeminiAI",
                    "Catch": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "Next": "HandleEmailFailure",
                        }
                    ],
                },
                "ProcessWithGeminiAI": {
                    "Type": "Task",
                    "Resource": query_gemini_ai_lambda.arn,
                    "Parameters": {
                        "s3_key.$": "$.s3_key",
                        "prompt.$": "$.prompt",
                    },
                    "ResultPath": "$.lambdaResult",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0,
                        }
                    ],
                    "Next": "UpdateCustomersFromEmail",
                    "Catch": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "Next": "HandleEmailFailure",
                        },
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandleEmailFailure",
                        },
                    ],
                },
                "UpdateCustomersFromEmail": {
                    "Type": "Task",
                    "Resource": update_customer_from_email_lambda.arn,
                    "Parameters": {
                        "lambdaResult.$": "$.lambdaResult",
                    },
                    "ResultPath": "$.customerUpdateResult",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0,
                        }
                    ],
                    "Next": "SaveEmailResult",
                    "Catch": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "Next": "HandleEmailFailure",
                        },
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandleEmailFailure",
                        },
                    ],
                },
                "SaveEmailResult": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:updateItem",
                    "Parameters": {
                        "TableName": email_processing_table.name,
                        "Key": {
                            "email_id": {"S.$": "$.email_id"},
                            "received_at": {"S.$": "$.email_metadata.received_at"},
                        },
                        "UpdateExpression": "SET #status = :status, completed_at = :completed_at, ai_result = :result, updated_at = :updated_at",
                        "ExpressionAttributeNames": {"#status": "status"},
                        "ExpressionAttributeValues": {
                            ":status": {"S": "COMPLETED"},
                            ":completed_at": {"S.$": "$$.State.EnteredTime"},
                            ":result": {"S.$": "$.lambdaResult.body"},
                            ":updated_at": {"S.$": "$$.State.EnteredTime"},
                        },
                    },
                    "End": True,
                },
                "HandleEmailFailure": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:updateItem",
                    "Parameters": {
                        "TableName": email_processing_table.name,
                        "Key": {
                            "email_id": {"S.$": "$.email_id"},
                            "received_at": {"S.$": "$.email_metadata.received_at"},
                        },
                        "UpdateExpression": "SET #status = :status, completed_at = :completed_at, error_message = :error, updated_at = :updated_at",
                        "ExpressionAttributeNames": {"#status": "status"},
                        "ExpressionAttributeValues": {
                            ":status": {"S": "FAILED"},
                            ":completed_at": {"S.$": "$$.State.EnteredTime"},
                            ":error": {"S.$": "$.Error"},
                            ":updated_at": {"S.$": "$$.State.EnteredTime"},
                        },
                    },
                    "End": True,
                },
            },
        }
    ),
    tags={
        "Name": f"{app_name}-email-processing-state-machine-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Photo analysis state machine will be defined after voice_ai_handler_lambda

# Lambda to start AI processing jobs
start_ai_job_lambda = lambda_.Function(
    f"{app_name}-start-ai-job-{stack_name}",
    runtime="python3.13",
    handler="start_ai_job.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/start_ai_job/lambda_function.zip"),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "START_AI_JOB_JOBS_TABLE_NAME": jobs_table.name,
            "START_AI_JOB_STATE_MACHINE_ARN": ai_processing_state_machine.arn,
        }
    ),
    tags={
        "Name": f"{app_name}-start-ai-job-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to check AI job status
get_ai_job_status_lambda = lambda_.Function(
    f"{app_name}-get-ai-job-status-{stack_name}",
    runtime="python3.13",
    handler="get_ai_job_status.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/get_ai_job_status/lambda_function.zip"),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "GET_AI_JOB_STATUS_JOBS_TABLE_NAME": jobs_table.name,
        }
    ),
    tags={
        "Name": f"{app_name}-get-ai-job-status-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to get user workflows
get_workflows_lambda = lambda_.Function(
    f"{app_name}-get-workflows-{stack_name}",
    runtime="python3.13",
    handler="get_workflows.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/get_workflows/lambda_function.zip"),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "WORKFLOWS_TABLE_NAME": workflows_table.name,
        }
    ),
    tags={
        "Name": f"{app_name}-get-workflows-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to create workflow
create_workflow_lambda = lambda_.Function(
    f"{app_name}-create-workflow-{stack_name}",
    runtime="python3.13",
    handler="create_workflow.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/create_workflow/lambda_function.zip"),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "WORKFLOWS_TABLE_NAME": workflows_table.name,
        }
    ),
    tags={
        "Name": f"{app_name}-create-workflow-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to get single workflow
get_workflow_lambda = lambda_.Function(
    f"{app_name}-get-workflow-{stack_name}",
    runtime="python3.13",
    handler="get_workflow.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/get_workflow/lambda_function.zip"),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "WORKFLOWS_TABLE_NAME": workflows_table.name,
            "TEMPLATE_SCHEMAS_TABLE_NAME": template_schemas_table.name,
        }
    ),
    tags={
        "Name": f"{app_name}-get-workflow-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to update workflow
update_workflow_lambda = lambda_.Function(
    f"{app_name}-update-workflow-{stack_name}",
    runtime="python3.13",
    handler="update_workflow.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/update_workflow/lambda_function.zip"),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "WORKFLOWS_TABLE_NAME": workflows_table.name,
        }
    ),
    tags={
        "Name": f"{app_name}-update-workflow-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to delete workflow
delete_workflow_lambda = lambda_.Function(
    f"{app_name}-delete-workflow-{stack_name}",
    runtime="python3.13",
    handler="delete_workflow.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/delete_workflow/lambda_function.zip"),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "DELETE_WORKFLOW_WORKFLOWS_TABLE_NAME": workflows_table.name,
        }
    ),
    tags={
        "Name": f"{app_name}-delete-workflow-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda for Assistant-UI Chat Handler
chat_handler_lambda = lambda_.Function(
    f"{app_name}-chat-handler-{stack_name}",
    runtime="python3.13",
    handler="chat_handler.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/chat_handler/lambda_function.zip"),
    role=upload_lambda_role.arn,
    timeout=config.get_int("lambda_timeout_seconds")
    or 900,  # Use existing timeout config or default
    memory_size=512,  # Adjust as needed
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "GEMINI_AI_GEMINI_API_KEY": config.require_secret("gemini_api_key"),
        }
    ),
    tags={
        "Name": f"{app_name}-chat-handler-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda for Customer CRM (must be defined before voice AI handler)
customer_crm_lambda = lambda_.Function(
    f"{app_name}-customer-crm-{stack_name}",
    runtime="python3.13",
    handler="customer_crm.main.lambda_handler",
    code=FileArchive("../apps/backend/functions/customer_crm/lambda_function.zip"),
    role=upload_lambda_role.arn,
    timeout=config.get_int("lambda_timeout_seconds") or 900,
    memory_size=512,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "CRM_CUSTOMERS_TABLE_NAME": customers_table.name,
            "CRM_AWS_REGION": aws_cfg.require("region"),
        }
    ),
    tags={
        "Name": f"{app_name}-customer-crm-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Additional policy for voice AI handler to invoke customer CRM Lambda
voice_ai_lambda_invoke_policy = iam.RolePolicy(
    f"{app_name}-voice-ai-lambda-invoke-policy",
    role=upload_lambda_role.id,
    policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["lambda:InvokeFunction"],
                    "Resource": [customer_crm_lambda.arn],
                }
            ],
        }
    ),
)

# Lambda for Voice AI Handler
voice_ai_handler_lambda = lambda_.Function(
    f"{app_name}-voice-ai-handler-{stack_name}",
    runtime="python3.13",
    handler="voice_ai_handler.main.lambda_handler",
    code=FileArchive("../apps/backend/functions/voice_ai_handler/lambda_function.zip"),
    role=upload_lambda_role.arn,
    timeout=config.get_int("lambda_timeout_seconds") or 900,
    memory_size=512,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "VOICE_AI_PROVIDER": voice_ai_cfg.get("provider"),
            "VOICE_AI_CUSTOMER_CRM_LAMBDA_NAME": customer_crm_lambda.name,
            "VAPI_API_KEY": vapi_cfg.require_secret("api_key"),
            "VAPI_WEBHOOK_SECRET": vapi_cfg.require_secret("webhook_secret"),
            "VAPI_PHONE_NUMBER_ID": vapi_cfg.get("phone_number_id"),
            "VAPI_DEFAULT_ASSISTANT_ID": vapi_cfg.get("default_assistant_id"),
            "VAPI_BASE_URL": vapi_cfg.get("base_url"),
            "VAPI_TIMEOUT": vapi_cfg.get("timeout") or "30",
            "VAPI_REQUIRE_WEBHOOK_VERIFICATION": vapi_cfg.get(
                "require_webhook_verification"
            )
            or "true",
        }
    ),
    tags={
        "Name": f"{app_name}-voice-ai-handler-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Step Functions State Machine for Photo Analysis
photo_analysis_state_machine = sfn.StateMachine(
    f"{app_name}-photo-analysis-state-machine-{stack_name}",
    name=f"{app_name}-photo-analysis-{stack_name}",
    role_arn=step_functions_role.arn,
    definition=pulumi.Output.json_dumps(
        {
            "Comment": "Photo analysis workflow with Gemini AI and Voice AI",
            "StartAt": "UpdatePhotoJobStatus",
            "States": {
                "UpdatePhotoJobStatus": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:updateItem",
                    "Parameters": {
                        "TableName": photo_analysis_table.name,
                        "Key": {"job_id": {"S.$": "$.job_id"}},
                        "UpdateExpression": "SET job_status = :status, started_at = :started_at, updated_at = :updated_at",
                        "ExpressionAttributeValues": {
                            ":status": {"S": "PROCESSING"},
                            ":started_at": {"S.$": "$$.State.EnteredTime"},
                            ":updated_at": {"S.$": "$$.State.EnteredTime"},
                        },
                    },
                    "ResultPath": "$.updateResult",
                    "Next": "ProcessWithGeminiAI",
                    "Catch": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "Next": "HandlePhotoFailure",
                        }
                    ],
                },
                "ProcessWithGeminiAI": {
                    "Type": "Task",
                    "Resource": query_gemini_ai_lambda.arn,
                    "Parameters": {
                        "s3_key.$": "$.s3_key",
                        "prompt": "Extract contact information from this photo. Look for name, company, phone number, email, and job title. Be as accurate as possible.",
                        "json_schema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Full name of the person in the photo",
                                },
                                "company": {
                                    "type": "string",
                                    "description": "Company or organization the person works for",
                                },
                                "phone_number": {
                                    "type": "string",
                                    "description": "Mobile phone number of the person",
                                },
                                "email": {
                                    "type": "string",
                                    "description": "Email address of the person (if visible)",
                                },
                                "title": {
                                    "type": "string",
                                    "description": "Job title or position of the person",
                                },
                            },
                            "required": [
                                "name",
                                "phone_number",
                                "company",
                            ],
                        },
                    },
                    "ResultPath": "$.lambdaResult",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0,
                        }
                    ],
                    "Next": "ParseGeminiResponse",
                    "Catch": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "Next": "HandlePhotoFailure",
                        },
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandlePhotoFailure",
                        },
                    ],
                },
                "ParseGeminiResponse": {
                    "Type": "Pass",
                    "Parameters": {
                        "s3_key.$": "$.s3_key",
                        "user_email.$": "$.user_email",
                        "job_id.$": "$.job_id",
                        "updateResult.$": "$.updateResult",
                        "lambdaResult.$": "$.lambdaResult",
                        "parsed_data.$": "$.lambdaResult.extracted",
                    },
                    "Next": "PrepareVoiceCall",
                },
                "PrepareVoiceCall": {
                    "Type": "Pass",
                    "Parameters": {
                        "s3_key.$": "$.s3_key",
                        "user_email.$": "$.user_email",
                        "job_id.$": "$.job_id",
                        "updateResult.$": "$.updateResult",
                        "lambdaResult.$": "$.lambdaResult",
                        "parsed_data.$": "$.parsed_data",
                        "rawPath": "/voice/outbound",
                        "body": {
                            "phone_number.$": "$.parsed_data.phone_number",
                            "adjuster_name.$": "$.parsed_data.name",
                            "company_name.$": "$.parsed_data.company",
                            "customer_id": "photo-analysis",
                            "metadata": {
                                "source": "photo_analysis",
                                "company.$": "$.parsed_data.company",
                            },
                        },
                    },
                    "Next": "InitiateVoiceCall",
                },
                "InitiateVoiceCall": {
                    "Type": "Task",
                    "Resource": voice_ai_handler_lambda.arn,
                    "Parameters": {
                        "rawPath.$": "$.rawPath",
                        "body.$": "States.JsonToString($.body)",
                    },
                    "ResultPath": "$.voiceResult",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0,
                        }
                    ],
                    "Next": "SavePhotoResult",
                    "Catch": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "Next": "HandlePhotoFailure",
                        },
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandlePhotoFailure",
                        },
                    ],
                },
                "SavePhotoResult": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:updateItem",
                    "Parameters": {
                        "TableName": photo_analysis_table.name,
                        "Key": {"job_id": {"S.$": "$.job_id"}},
                        "UpdateExpression": "SET job_status = :status, completed_at = :completed_at, ai_result = :result, voice_call_id = :call_id, voice_result = :voice_result, updated_at = :updated_at",
                        "ExpressionAttributeValues": {
                            ":status": {"S": "COMPLETED"},
                            ":completed_at": {"S.$": "$$.State.EnteredTime"},
                            ":result": {"S.$": "$.lambdaResult.body"},
                            ":call_id": {"S": "N/A"},
                            ":voice_result": {"S.$": "$.voiceResult.body"},
                            ":updated_at": {"S.$": "$$.State.EnteredTime"},
                        },
                    },
                    "End": True,
                },
                "HandlePhotoFailure": {
                    "Type": "Task",
                    "Resource": "arn:aws-us-gov:states:::dynamodb:updateItem",
                    "Parameters": {
                        "TableName": photo_analysis_table.name,
                        "Key": {"job_id": {"S.$": "$.job_id"}},
                        "UpdateExpression": "SET job_status = :status, completed_at = :completed_at, error_message = :error, updated_at = :updated_at",
                        "ExpressionAttributeValues": {
                            ":status": {"S": "FAILED"},
                            ":completed_at": {"S.$": "$$.State.EnteredTime"},
                            ":error": {"S.$": "$.Error"},
                            ":updated_at": {"S.$": "$$.State.EnteredTime"},
                        },
                    },
                    "End": True,
                },
            },
        }
    ),
    tags={
        "Name": f"{app_name}-photo-analysis-state-machine-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda for Email Webhook Handler
email_webhook_lambda = lambda_.Function(
    f"{app_name}-email-webhook-{stack_name}",
    runtime="python3.13",
    handler="email_webhook.handler.lambda_handler",
    code=FileArchive("../apps/backend/functions/email_webhook/lambda_function.zip"),
    role=upload_lambda_role.arn,
    timeout=30,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "EMAIL_CONTENT_BUCKET": email_content_bucket.bucket,
            "EMAIL_PROCESSING_TABLE_NAME": email_processing_table.name,
            "EMAIL_PROCESSING_STATE_MACHINE_ARN": email_processing_state_machine.arn,
            "EMAIL_PLATFORM": email_cfg.get("platform") or "zapier",
        }
    ),
    tags={
        "Name": f"{app_name}-email-webhook-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to start email processing jobs
start_email_processing_lambda = lambda_.Function(
    f"{app_name}-start-email-processing-{stack_name}",
    runtime="python3.13",
    handler="start_email_processing.handler.lambda_handler",
    code=FileArchive(
        "../apps/backend/functions/start_email_processing/lambda_function.zip"
    ),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "EMAIL_PROCESSING_TABLE_NAME": email_processing_table.name,
            "EMAIL_PROCESSING_STATE_MACHINE_ARN": email_processing_state_machine.arn,
        }
    ),
    tags={
        "Name": f"{app_name}-start-email-processing-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Lambda to start photo analysis jobs
start_photo_analysis_lambda = lambda_.Function(
    f"{app_name}-start-photo-analysis-{stack_name}",
    runtime="python3.13",
    handler="start_photo_analysis.handler.lambda_handler",
    code=FileArchive(
        "../apps/backend/functions/start_photo_analysis/lambda_function.zip"
    ),
    role=upload_lambda_role.arn,
    environment=lambda_.FunctionEnvironmentArgs(
        variables={
            "PHOTO_ANALYSIS_TABLE_NAME": photo_analysis_table.name,
            "PHOTO_ANALYSIS_STATE_MACHINE_ARN": photo_analysis_state_machine.arn,
        }
    ),
    tags={
        "Name": f"{app_name}-start-photo-analysis-lambda-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# API Gateway HTTP API
upload_api = apigatewayv2.Api(
    f"{app_name}-upload-api-{stack_name}",
    protocol_type="HTTP",
    route_selection_expression="$request.method $request.path",
    cors_configuration=apigatewayv2.ApiCorsConfigurationArgs(
        allow_origins=[
            app_domain_url,
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["authorization", "content-type"],
        allow_credentials=True,
        max_age=300,
    ),
    tags={
        "Name": f"{app_name}-upload-api-{environment}",
        "Environment": environment,
        "Stack": stack_name,
    },
)

# Cognito Authorizer for API Gateway
cognito_authorizer = apigatewayv2.Authorizer(
    f"{app_name}-cognito-authorizer-{stack_name}",
    api_id=upload_api.id,
    authorizer_type="JWT",
    identity_sources=["$request.header.Authorization"],
    name=f"{app_name}-cognito-authorizer",
    jwt_configuration=apigatewayv2.AuthorizerJwtConfigurationArgs(
        audiences=[pool_client.id],
        issuer=pulumi.Output.format(
            "https://cognito-idp.{}.amazonaws.com/{}",
            aws_cfg.require("region"),
            user_pool.id,
        ),
    ),
)

# Integration for presigned URL Lambda
get_url_integration = apigatewayv2.Integration(
    f"{app_name}-get-url-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=get_upload_url_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for GET /upload-url
get_url_route = apigatewayv2.Route(
    f"{app_name}-get-url-route-{stack_name}",
    api_id=upload_api.id,
    route_key="GET /upload-url",
    target=pulumi.Output.concat("integrations/", get_url_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for metadata record Lambda
create_record_integration = apigatewayv2.Integration(
    f"{app_name}-create-record-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=create_upload_record_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for POST /upload-record
create_record_route = apigatewayv2.Route(
    f"{app_name}-create-record-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /upload-record",
    target=pulumi.Output.concat("integrations/", create_record_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for start AI job Lambda
start_ai_job_integration = apigatewayv2.Integration(
    f"{app_name}-start-ai-job-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=start_ai_job_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for POST /query-gemini-ai (now starts async job)
start_ai_job_route = apigatewayv2.Route(
    f"{app_name}-start-ai-job-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /query-gemini-ai",
    target=pulumi.Output.concat("integrations/", start_ai_job_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for Pulse AI Lambda
query_pulse_ai_integration = apigatewayv2.Integration(
    f"{app_name}-query-pulse-ai-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=query_pulse_ai_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for POST /query-pulse-ai
query_pulse_ai_route = apigatewayv2.Route(
    f"{app_name}-query-pulse-ai-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /query-pulse-ai",
    target=pulumi.Output.concat("integrations/", query_pulse_ai_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for get AI job status Lambda
get_ai_job_status_integration = apigatewayv2.Integration(
    f"{app_name}-get-ai-job-status-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=get_ai_job_status_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for GET /query-gemini-ai/status/{job_id}
get_ai_job_status_route = apigatewayv2.Route(
    f"{app_name}-get-ai-job-status-route-{stack_name}",
    api_id=upload_api.id,
    route_key="GET /query-gemini-ai/status/{job_id}",
    target=pulumi.Output.concat("integrations/", get_ai_job_status_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for get workflows Lambda
get_workflows_integration = apigatewayv2.Integration(
    f"{app_name}-get-workflows-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=get_workflows_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for GET /workflows
get_workflows_route = apigatewayv2.Route(
    f"{app_name}-get-workflows-route-{stack_name}",
    api_id=upload_api.id,
    route_key="GET /workflows",
    target=pulumi.Output.concat("integrations/", get_workflows_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for create workflow Lambda
create_workflow_integration = apigatewayv2.Integration(
    f"{app_name}-create-workflow-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=create_workflow_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for POST /workflows
create_workflow_route = apigatewayv2.Route(
    f"{app_name}-create-workflow-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /workflows",
    target=pulumi.Output.concat("integrations/", create_workflow_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for get workflow Lambda
get_workflow_integration = apigatewayv2.Integration(
    f"{app_name}-get-workflow-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=get_workflow_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for GET /workflows/{workflow_id}
get_workflow_route = apigatewayv2.Route(
    f"{app_name}-get-workflow-route-{stack_name}",
    api_id=upload_api.id,
    route_key="GET /workflows/{workflow_id}",
    target=pulumi.Output.concat("integrations/", get_workflow_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for update workflow Lambda
update_workflow_integration = apigatewayv2.Integration(
    f"{app_name}-update-workflow-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=update_workflow_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for PUT /workflows/{workflow_id}
update_workflow_route = apigatewayv2.Route(
    f"{app_name}-update-workflow-route-{stack_name}",
    api_id=upload_api.id,
    route_key="PUT /workflows/{workflow_id}",
    target=pulumi.Output.concat("integrations/", update_workflow_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for delete workflow Lambda
delete_workflow_integration = apigatewayv2.Integration(
    f"{app_name}-delete-workflow-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=delete_workflow_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for DELETE /workflows/{workflow_id}
delete_workflow_route = apigatewayv2.Route(
    f"{app_name}-delete-workflow-route-{stack_name}",
    api_id=upload_api.id,
    route_key="DELETE /workflows/{workflow_id}",
    target=pulumi.Output.concat("integrations/", delete_workflow_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

process_template_integration = apigatewayv2.Integration(
    f"{app_name}-process-template-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=process_template_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for POST /process-template
process_template_route = apigatewayv2.Route(
    f"{app_name}-process-template-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /process-template",
    target=pulumi.Output.concat("integrations/", process_template_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for chat handler Lambda
chat_handler_integration = apigatewayv2.Integration(
    f"{app_name}-chat-handler-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=chat_handler_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Integration for voice AI handler Lambda
voice_ai_handler_integration = apigatewayv2.Integration(
    f"{app_name}-voice-ai-handler-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=voice_ai_handler_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Integration for customer CRM Lambda
customer_crm_integration = apigatewayv2.Integration(
    f"{app_name}-customer-crm-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=customer_crm_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for POST /chat (Assistant-UI endpoint)
chat_handler_route = apigatewayv2.Route(
    f"{app_name}-chat-handler-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /chat",
    target=pulumi.Output.concat("integrations/", chat_handler_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Routes for Voice AI Handler
voice_ai_outbound_route = apigatewayv2.Route(
    f"{app_name}-voice-ai-outbound-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /voice/outbound",
    target=pulumi.Output.concat("integrations/", voice_ai_handler_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

voice_ai_webhook_route = apigatewayv2.Route(
    f"{app_name}-voice-ai-webhook-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /voice/webhook",
    target=pulumi.Output.concat("integrations/", voice_ai_handler_integration.id),
    # No authorization for webhooks - they use their own verification
)

# Integration for email webhook Lambda
email_webhook_integration = apigatewayv2.Integration(
    f"{app_name}-email-webhook-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=email_webhook_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for email webhook (no authorization for webhooks)
email_webhook_route = apigatewayv2.Route(
    f"{app_name}-email-webhook-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /email/webhook",
    target=pulumi.Output.concat("integrations/", email_webhook_integration.id),
    # No authorization for webhooks - they use their own verification
)

# Integration for start email processing Lambda
start_email_processing_integration = apigatewayv2.Integration(
    f"{app_name}-start-email-processing-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=start_email_processing_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for POST /start-email-processing
start_email_processing_route = apigatewayv2.Route(
    f"{app_name}-start-email-processing-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /start-email-processing",
    target=pulumi.Output.concat("integrations/", start_email_processing_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Integration for start photo analysis Lambda
start_photo_analysis_integration = apigatewayv2.Integration(
    f"{app_name}-start-photo-analysis-integration-{stack_name}",
    api_id=upload_api.id,
    integration_type="AWS_PROXY",
    integration_uri=start_photo_analysis_lambda.invoke_arn,
    payload_format_version="2.0",
)

# Route for POST /start-photo-analysis
start_photo_analysis_route = apigatewayv2.Route(
    f"{app_name}-start-photo-analysis-route-{stack_name}",
    api_id=upload_api.id,
    route_key="POST /start-photo-analysis",
    target=pulumi.Output.concat("integrations/", start_photo_analysis_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)
# Routes for Customer CRM
customer_crm_search_route = apigatewayv2.Route(
    f"{app_name}-customer-crm-search-route-{stack_name}",
    api_id=upload_api.id,
    route_key="GET /customers",
    target=pulumi.Output.concat("integrations/", customer_crm_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

customer_crm_get_route = apigatewayv2.Route(
    f"{app_name}-customer-crm-get-route-{stack_name}",
    api_id=upload_api.id,
    route_key="GET /customers/{customer_id}",
    target=pulumi.Output.concat("integrations/", customer_crm_integration.id),
    authorization_type="JWT",
    authorizer_id=cognito_authorizer.id,
)

# Stage for automatic deployment
upload_stage = apigatewayv2.Stage(
    f"{app_name}-upload-stage-{stack_name}",
    api_id=upload_api.id,
    name="$default",
    auto_deploy=True,
)

# Permissions for API Gateway to invoke Lambdas
get_url_permission = lambda_.Permission(
    f"{app_name}-get-url-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=get_upload_url_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

create_record_permission = lambda_.Permission(
    f"{app_name}-create-record-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=create_upload_record_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

start_ai_job_permission = lambda_.Permission(
    f"{app_name}-start-ai-job-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=start_ai_job_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

# Permission for Pulse AI Lambda
query_pulse_ai_permission = lambda_.Permission(
    f"{app_name}-query-pulse-ai-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=query_pulse_ai_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

get_ai_job_status_permission = lambda_.Permission(
    f"{app_name}-get-ai-job-status-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=get_ai_job_status_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

# Permissions for workflow Lambda functions
get_workflows_permission = lambda_.Permission(
    f"{app_name}-get-workflows-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=get_workflows_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

create_workflow_permission = lambda_.Permission(
    f"{app_name}-create-workflow-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=create_workflow_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

get_workflow_permission = lambda_.Permission(
    f"{app_name}-get-workflow-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=get_workflow_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

update_workflow_permission = lambda_.Permission(
    f"{app_name}-update-workflow-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=update_workflow_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

delete_workflow_permission = lambda_.Permission(
    f"{app_name}-delete-workflow-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=delete_workflow_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

process_template_permission = lambda_.Permission(
    f"{app_name}-process-template-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=process_template_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

chat_handler_permission = lambda_.Permission(
    f"{app_name}-chat-handler-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=chat_handler_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

voice_ai_handler_permission = lambda_.Permission(
    f"{app_name}-voice-ai-handler-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=voice_ai_handler_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

email_webhook_permission = lambda_.Permission(
    f"{app_name}-email-webhook-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=email_webhook_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

start_email_processing_permission = lambda_.Permission(
    f"{app_name}-start-email-processing-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=start_email_processing_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

start_photo_analysis_permission = lambda_.Permission(
    f"{app_name}-start-photo-analysis-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=start_photo_analysis_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

customer_crm_permission = lambda_.Permission(
    f"{app_name}-customer-crm-permission-{stack_name}",
    action="lambda:InvokeFunction",
    function=customer_crm_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=upload_api.execution_arn.apply(lambda arn: f"{arn}/*"),
)

# Build and push web app Docker image (conditional)
web_image = None
if deploy_containers:
    web_image = docker_build.Image(
        f"{web_app_name}-image",
        context=docker_build.BuildContextArgs(
            location="../",  # Monorepo root
        ),
        dockerfile=docker_build.DockerfileArgs(
            location="../apps/web/Dockerfile",
        ),
        platforms=["linux/amd64"],  # Ensure compatibility with AWS Fargate
        build_args={
            "PUBLIC_SERVER_URL": app_domain_url,
            "PUBLIC_BASE_PATH": config.require("public_base_path"),
            "PUBLIC_COGNITO_DOMAIN": cognito_domain_url,
            "PUBLIC_COGNITO_CLIENT_ID": pool_client.id,
            "PUBLIC_COGNITO_SCOPES": config.require("public_cognito_scopes"),
            "PUBLIC_OAUTH_REDIRECT_ROUTE": config.require("oauth_redirect_route"),
            "PUBLIC_SERVERLESS_API_URL": upload_api.api_endpoint,
        },
        tags=[web_ecr_repository.repository_url.apply(lambda url: f"{url}:latest")],
        push=True,
        registries=[
            docker_build.RegistryArgs(
                address=web_ecr_repository.repository_url,
                username=auth_token.user_name,
                password=pulumi.Output.secret(auth_token.password),
            )
        ],
    )

# ECS Task Definition (conditional)
task_definition = None
if deploy_containers:
    task_definition = ecs.TaskDefinition(
        f"{server_app_name}-task-def-{stack_name}",
        family=f"{server_app_name}",
        network_mode="awsvpc",
        requires_compatibilities=["FARGATE"],
        cpu="256",
        memory="512",
        execution_role_arn=task_execution_role.arn,
        task_role_arn=task_role.arn,
        container_definitions=pulumi.Output.json_dumps(
            [
                {
                    "name": f"{server_app_name}-container",
                    "image": server_image.ref,  # Use the built image
                    "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
                    "environment": [
                        {"name": "ENVIRONMENT", "value": environment},
                        {"name": "CLIENT_BASE_URL", "value": app_domain_url},
                        {
                            "name": "AWS_REGION",
                            "value": aws_cfg.require("region"),
                        },
                        {
                            "name": "COGNITO_USER_POOL_ID",
                            "value": user_pool.id,
                        },
                        {
                            "name": "COGNITO_CLIENT_ID",
                            "value": pool_client.id,
                        },
                        {
                            "name": "COGNITO_CLIENT_SECRET",
                            "value": pool_client.client_secret,
                        },
                        {
                            "name": "COGNITO_DOMAIN",
                            "value": cognito_domain_url,
                        },
                        {
                            "name": "OAUTH_REDIRECT_URI",
                            "value": oauth_redirect_uri,
                        },
                        {"name": "OAUTH_SCOPE", "value": config.require("oauth_scope")},
                        {
                            "name": "COOKIE_DOMAIN",
                            "value": certificate_domain,
                        },
                        {
                            "name": "AUTH_SESSION_TIMEOUT_HOURS",
                            "value": config.require("auth_session_timeout_hours"),
                        },
                        {
                            "name": "AUTH_REFRESH_TOKEN_TIMEOUT_DAYS",
                            "value": config.require("auth_session_token_timeout_days"),
                        },
                        {
                            "name": "COOKIE_SECURE",
                            "value": config.require("cookie_secure"),
                        },
                        {
                            "name": "COOKIE_SAMESITE",
                            "value": config.require("cookie_samesite"),
                        },
                        {
                            "name": "COOKIE_HTTPONLY",
                            "value": config.require("cookie_httponly"),
                        },
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": log_group.name,
                            "awslogs-region": "us-gov-west-1",
                            "awslogs-stream-prefix": "ecs",
                        },
                    },
                    "healthCheck": {
                        "command": [
                            "CMD-SHELL",
                            "curl -f http://localhost:8080/healthcheck || exit 1",
                        ],
                        "interval": 30,
                        "timeout": 5,
                        "retries": 3,
                        "startPeriod": 60,
                    },
                }
            ]
        ),
        tags={
            "Name": f"{server_app_name}-task-def",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# Web App Task Definition (conditional)
web_task_definition = None
if deploy_containers:
    web_task_definition = ecs.TaskDefinition(
        f"{web_app_name}-task-{stack_name}",
        family=f"{web_app_name}-task",
        cpu="256",
        memory="512",
        network_mode="awsvpc",
        requires_compatibilities=["FARGATE"],
        execution_role_arn=task_execution_role.arn,
        task_role_arn=task_role.arn,
        container_definitions=pulumi.Output.json_dumps(
            [
                {
                    "name": "nginx",
                    "image": web_image.ref,  # Use the built image
                    "portMappings": [
                        {
                            "containerPort": 80,
                            "hostPort": 80,
                            "protocol": "tcp",
                        }
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": log_group.name,
                            "awslogs-region": "us-gov-west-1",
                            "awslogs-stream-prefix": "nginx",
                        },
                    },
                    "essential": True,
                }
            ]
        ),
        tags={
            "Name": f"{web_app_name}-task",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# ECS Service (conditional)
service = None
if deploy_containers:
    service = ecs.Service(
        f"{server_app_name}-service-{stack_name}",
        name=f"{server_app_name}-{stack_name}",
        cluster=cluster.arn,
        task_definition=task_definition.arn,
        desired_count=1,
        launch_type="FARGATE",
        network_configuration=ecs.ServiceNetworkConfigurationArgs(
            assign_public_ip=True,
            subnets=[public_subnet_1.id, public_subnet_2.id],
            security_groups=[ecs_security_group.id],
        ),
        load_balancers=[
            ecs.ServiceLoadBalancerArgs(
                target_group_arn=target_group.arn,
                container_name=f"{server_app_name}-container",
                container_port=8080,
            )
        ],
        opts=pulumi.ResourceOptions(
            depends_on=[alb_listener_rule_api] if deploy_containers else None
        ),  # Depend on the listener rule only if frontend is deployed
        tags={
            "Name": f"{server_app_name}-service",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# Web App ECS Service (conditional)
web_service = None
if deploy_containers:
    web_service = ecs.Service(
        f"{web_app_name}-service-{stack_name}",
        name=f"{web_app_name}-{stack_name}",
        cluster=cluster.arn,
        task_definition=web_task_definition.arn,
        desired_count=1,
        launch_type="FARGATE",
        network_configuration=ecs.ServiceNetworkConfigurationArgs(
            assign_public_ip=True,
            subnets=[public_subnet_1.id, public_subnet_2.id],
            security_groups=[web_security_group.id],
        ),
        load_balancers=[
            ecs.ServiceLoadBalancerArgs(
                target_group_arn=web_target_group.arn,
                container_name="nginx",
                container_port=80,
            )
        ],
        opts=pulumi.ResourceOptions(depends_on=[https_listener]),
        tags={
            "Name": f"{web_app_name}-service",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

# Exports
pulumi.export("vpc_id", vpc.id)
pulumi.export("cluster_name", cluster.name)
pulumi.export("log_group_name", log_group.name)
pulumi.export("cognito_user_pool_id", user_pool.id)
pulumi.export("cognito_user_pool_client_id", pool_client.id)
pulumi.export("cognito_user_pool_client_secret", pool_client.client_secret)
pulumi.export("uploadBucketName", upload_bucket.bucket)
pulumi.export("uploadTableName", upload_table.name)
pulumi.export("jobsTableName", jobs_table.name)
pulumi.export("workflowsTableName", workflows_table.name)
pulumi.export("customersTableName", customers_table.name)
pulumi.export("uploadApiEndpoint", upload_api.api_endpoint)
pulumi.export("geminiAiLambdaUrn", query_gemini_ai_lambda.urn)
pulumi.export("pulseAiLambdaUrn", query_pulse_ai_lambda.urn)
pulumi.export("aiProcessingStateMachineArn", ai_processing_state_machine.arn)
pulumi.export("emailProcessingStateMachineArn", email_processing_state_machine.arn)
pulumi.export("startAiJobLambdaUrn", start_ai_job_lambda.urn)
pulumi.export("getAiJobStatusLambdaUrn", get_ai_job_status_lambda.urn)
pulumi.export("emailContentBucketName", email_content_bucket.bucket)
pulumi.export("emailProcessingTableName", email_processing_table.name)
pulumi.export("emailWebhookLambdaUrn", email_webhook_lambda.urn)
pulumi.export("photoAnalysisTableName", photo_analysis_table.name)
pulumi.export("photoAnalysisStateMachineArn", photo_analysis_state_machine.arn)
pulumi.export("startPhotoAnalysisLambdaUrn", start_photo_analysis_lambda.urn)

# Conditional container exports
if deploy_containers:
    pulumi.export("service_name", service.name)
    pulumi.export("task_definition_arn", task_definition.arn)
    pulumi.export("ecr_repository_url", ecr_repository.repository_url)
    pulumi.export("alb_dns_name", alb.dns_name)
    pulumi.export("web_ecr_repository_url", web_ecr_repository.repository_url)
    pulumi.export("ssl_certificate_arn", ssl_certificate.arn)

# Grant Lambda permission to start the AI processing state machine
lambda_start_sfn_policy = iam.RolePolicy(
    f"{app_name}-lambda-start-sfn-policy-{stack_name}",
    role=upload_lambda_role.id,
    policy=pulumi.Output.json_dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "states:StartExecution",
                        "states:DescribeExecution",
                        "states:StopExecution",
                    ],
                    "Resource": [
                        ai_processing_state_machine.arn,
                        email_processing_state_machine.arn,
                        photo_analysis_state_machine.arn,
                    ],
                }
            ],
        }
    ),
)
