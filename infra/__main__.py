"""AWS Infrastructure for Maive application using Pulumi"""

import time

import pulumi
import pulumi_docker_build as docker_build
from pulumi_aws import (
    acm,
    apigatewayv2,
    cloudwatch,
    cognito,
    ec2,
    ecr,
    ecs,
    iam,
    lb,
    route53,
    s3,
)

# Configuration
config = pulumi.Config()
aws_cfg = pulumi.Config("aws")
s3_cfg = pulumi.Config("s3")

# Get stack name for dynamic resource naming
stack_name = pulumi.get_stack()
environment = config.require("environment")

certificate_domain = config.require("certificate_domain")
deploy_containers = config.require_bool("deploy_containers")
force_destroy_buckets = s3_cfg.get_bool("force_destroy") or False

app_name = pulumi.get_project()
server_app_name = f"{app_name}-server"
web_app_name = f"{app_name}-web"

# Generate timestamp-based tags for immutable deployments
timestamp = int(time.time())
server_image_tag = f"{server_app_name}-{timestamp}"
web_image_tag = f"{web_app_name}-{timestamp}"

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
    availability_zone=f"{aws_cfg.require('region')}a",
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
    availability_zone=f"{aws_cfg.require('region')}c",
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
        "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
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
        image_tag_mutability="IMMUTABLE",
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
        image_tag_mutability="IMMUTABLE",
        image_scanning_configuration=ecr.RepositoryImageScanningConfigurationArgs(
            scan_on_push=True,
        ),
        tags={
            "Name": f"{web_app_name}-repo",
            "Environment": environment,
            "Stack": stack_name,
        },
    )

    # ECR Lifecycle policies (expire untagged images after 14 days)
    ecr.LifecyclePolicy(
        f"{server_app_name}-repo-lifecycle-{stack_name}",
        repository=ecr_repository.name,
        policy=pulumi.Output.json_dumps(
            {
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Expire untagged after 14 days",
                        "selection": {
                            "tagStatus": "untagged",
                            "countType": "sinceImagePushed",
                            "countUnit": "days",
                            "countNumber": 14,
                        },
                        "action": {"type": "expire"},
                    }
                ]
            }
        ),
    )
    ecr.LifecyclePolicy(
        f"{web_app_name}-repo-lifecycle-{stack_name}",
        repository=web_ecr_repository.name,
        policy=pulumi.Output.json_dumps(
            {
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Expire untagged after 14 days",
                        "selection": {
                            "tagStatus": "untagged",
                            "countType": "sinceImagePushed",
                            "countUnit": "days",
                            "countNumber": 14,
                        },
                        "action": {"type": "expire"},
                    }
                ]
            }
        ),
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
        tags=[
            ecr_repository.repository_url.apply(
                lambda url: f"{url}:{server_image_tag}"
            ),
            ecr_repository.repository_url.apply(lambda url: f"{url}:latest"),
        ],
        push=True,
        registries=[
            docker_build.RegistryArgs(
                address=ecr_repository.repository_url,
                username=auth_token.user_name,
                password=pulumi.Output.secret(auth_token.password),
            )
        ],
    )

    # Explicit image reference for task definition
    server_image_ref = ecr_repository.repository_url.apply(
        lambda url: f"{url}:{server_image_tag}"
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
    mfa_configuration="OFF",
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
    domain=f"{stack_name}-maive-{environment}",
    user_pool_id=user_pool.id,
    managed_login_version=2,
)

# Construct the Cognito domain URL
cognito_domain_url = pulumi.Output.format(
    "https://{}.auth.{}.amazoncognito.com",
    user_pool_domain.domain,
    aws_cfg.require("region"),
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
            "PUBLIC_SERVER_URL": config.require("public_server_url"),
            "PUBLIC_BASE_PATH": config.require("public_base_path"),
            "PUBLIC_COGNITO_DOMAIN": cognito_domain_url,
            "PUBLIC_COGNITO_CLIENT_ID": pool_client.id,
            "PUBLIC_COGNITO_SCOPES": config.require("public_cognito_scopes"),
            "PUBLIC_OAUTH_REDIRECT_ROUTE": config.require("oauth_redirect_route"),
        },
        tags=[
            web_ecr_repository.repository_url.apply(
                lambda url: f"{url}:{web_image_tag}"
            ),
            web_ecr_repository.repository_url.apply(lambda url: f"{url}:latest"),
        ],
        push=True,
        registries=[
            docker_build.RegistryArgs(
                address=web_ecr_repository.repository_url,
                username=auth_token.user_name,
                password=pulumi.Output.secret(auth_token.password),
            )
        ],
    )

    web_image_ref = web_ecr_repository.repository_url.apply(
        lambda url: f"{url}:{web_image_tag}"
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
                    "image": server_image_ref,  # Use the immutable tag
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
                            "awslogs-region": aws_cfg.require("region"),
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
                    "image": web_image_ref,  # Use the immutable tag
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
                            "awslogs-region": aws_cfg.require("region"),
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
        deployment_circuit_breaker={
            "enable": True,
            "rollback": True,
        },
        deployment_maximum_percent=200,
        deployment_minimum_healthy_percent=100,
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
        desired_count=2,
        deployment_circuit_breaker={
            "enable": True,
            "rollback": True,
        },
        deployment_maximum_percent=200,
        deployment_minimum_healthy_percent=100,
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
pulumi.export("uploadApiEndpoint", upload_api.api_endpoint)

# Conditional container exports
if deploy_containers:
    pulumi.export("service_name", service.name)
    pulumi.export("task_definition_arn", task_definition.arn)
    pulumi.export("ecr_repository_url", ecr_repository.repository_url)
    pulumi.export("alb_dns_name", alb.dns_name)
    pulumi.export("web_ecr_repository_url", web_ecr_repository.repository_url)
    pulumi.export("ssl_certificate_arn", ssl_certificate.arn)
