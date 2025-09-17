#!/usr/bin/env python3
"""
Deployment script for Maive server application.

This script builds the Docker image, pushes it to ECR, and updates the ECS service.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(
    command: list[str], cwd: Path | None = None
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    return result


def get_ecr_login_token(region: str) -> str:
    """Get ECR login token."""
    result = run_command(["aws", "ecr", "get-login-password", "--region", region])
    return result.stdout.strip()


def docker_login(registry: str, token: str) -> None:
    """Login to Docker registry."""
    command = ["docker", "login", "--username", "AWS", "--password-stdin", registry]
    process = subprocess.run(
        command, input=token, capture_output=True, text=True, check=True
    )
    print(process.stdout)
    if process.stderr:
        print(process.stderr, file=sys.stderr)


def build_and_push_image(
    ecr_repo_url: str,
    dockerfile_path: Path,
    context_path: Path,
    tag: str = "latest",
) -> None:
    """Build and push Docker image to ECR."""
    full_image_name = f"{ecr_repo_url}:{tag}"

    # Build the image
    run_command(
        [
            "docker",
            "build",
            "-f",
            str(dockerfile_path),
            "-t",
            full_image_name,
            str(context_path),
        ]
    )

    # Push the image
    run_command(["docker", "push", full_image_name])


def update_ecs_service(cluster_name: str, service_name: str, region: str) -> None:
    """Update ECS service to use the latest task definition."""
    # Force new deployment
    run_command(
        [
            "aws",
            "ecs",
            "update-service",
            "--cluster",
            cluster_name,
            "--service",
            service_name,
            "--force-new-deployment",
            "--region",
            region,
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Deploy Maive server to ECS")
    parser.add_argument(
        "--environment", required=True, choices=["dev", "staging", "prod"]
    )
    parser.add_argument("--region", default="us-gov-west-1")
    parser.add_argument("--tag", default="latest")
    parser.add_argument(
        "--skip-build", action="store_true", help="Skip Docker build and push"
    )

    args = parser.parse_args()

    # Configuration
    app_name = "maive-server"
    cluster_name = f"{app_name}-{args.environment}"
    service_name = f"{app_name}-{args.environment}"
    ecr_repo_name = f"{app_name}-{args.environment}"
    ecr_repo_url = f"{args.region}.amazonaws.com/{ecr_repo_name}"

    # Paths
    project_root = Path(__file__).parent.parent
    dockerfile_path = project_root / "apps" / "server" / "Dockerfile"
    context_path = project_root

    print(f"Deploying {app_name} to {args.environment} environment")
    print(f"ECR Repository: {ecr_repo_url}")
    print(f"ECS Cluster: {cluster_name}")
    print(f"ECS Service: {service_name}")

    if not args.skip_build:
        print("\n1. Logging into ECR...")
        token = get_ecr_login_token(args.region)
        docker_login(ecr_repo_url, token)

        print("\n2. Building and pushing Docker image...")
        build_and_push_image(ecr_repo_url, dockerfile_path, context_path, args.tag)

    print("\n3. Updating ECS service...")
    update_ecs_service(cluster_name, service_name, args.region)

    print(f"\n✅ Deployment complete! Service {service_name} is being updated.")
    print(
        f"Monitor the deployment with: aws ecs describe-services --cluster {cluster_name} --services {service_name} --region {args.region}"
    )


if __name__ == "__main__":
    main()
