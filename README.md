# Quick Start

## Prerequisites

### Install nvm

- curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
- source ~/.zshrc

### Setup Node and pnpm

- In the directory:
- nvm install
- corepack enable
- pnpm --version
  -- This should match the "packageManager" version in package.json exactly
- pnpm install

## Install all dependencies for apps and packages
pnpm install

### Setup Server
1. Install UV on machine
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

You can then start all applications with

```bash
pnpm dev
```

By default the following URLs will be accessible:

- web application: http://localhost:3000
- backend server: http://localhost:8080

### Setup AWS

1. **Get Account Access**
   - Have Will provision an account for you
   - Accept the email invite

2. **Install AWS CLI**
   ```bash
   brew install awscli
   ```

3. Setup aws cli credentials
   - Have Will create an IAM user for you and get your access keys
   - Run `aws configure` and add the values in [this guide](https://docs.aws.amazon.com/cli/v1/userguide/cli-authentication-user)html]
   - Verify that it's functional with `aws sts get-caller-identity`

3. **ARCHIVED - DONT DO THIS IF YOURE GOING TO USE PULUMI - Configure SSO Profile**
   ```bash
   aws configure sso
   ```
   - `SSO session name: dev-session`
   - `SSO start URL: https://start.us-west-1.us-gov-home.awsapps.com/directory/d-98677f964b#`
   - `SSO region: us-west-1`
   - `SSO registration scopes: sso:account:access`
   - Select `developer` role
   - `Default client Region [None]: us-west-1`
   - `CLI default output format (json if not specified) [None]: <hit-enter>`
   - `Profile name [developer-416450511684]: dev`
   - Login: `aws sso login --profile dev`
   - Verify that it works `aws sts get-caller-identity --profile dev`
   - **Note**: Credentials expire after ~12 hours

## Setup Precommit hooks
`pnpm dlx husky install`
`pnpm install`

## Install pulumi
`brew install pulumi/tap/pulumi`
`brew update && brew install pulumi/tap/esc`

## API Development Guidelines

### Adding New APIs

To maintain consistent frontend API architecture, follow the **Generated API Client Pattern**:

3. **Create Frontend Client**: In `apps/web/src/clients/`, create a wrapper client
   - Import `Configuration` and the generated API class
   - Create async factory function using `getIdToken()` and `env.PUBLIC_SERVERLESS_API_URL`
   - Export wrapper functions that call the generated API methods
   - Re-export types from the generated client

4. **Backend Implementation**: Ensure Lambda functions match the OpenAPI spec
   - Request/response formats must align with defined schemas
   - Handle authentication and authorization properly

This pattern ensures type safety, consistent error handling, and maintainable API integrations across the frontend.

## Developing

### Working with a single package

Use [`pnpm --filter=<name>`](https://pnpm.io/filtering) (where `<name>` is
defined in the `package.json` of each package).

Example usage:

```bash
# Install the nuqs package for our web application:
pnpm --filter=web install nuqs

# Format only the ui package:
pnpm --filter=@maive/ui format
```

You can get a list of all package names using the command below:

```bash
find . -maxdepth 3 -name "package.json" -exec grep '"name":' {} \;
```

### Tooling Scripts

All scripts are defined in [package.json](package.json) and
[turbo.json](turbo.json):

```bash
pnpm clean                  # remove all .cache, .turbo, dist, node_modules

pnpm typecheck              # report typescript issues

pnpm format                 # report prettier issues
pnpm format:fix             # auto-fix prettier issues

pnpm lint                   # report eslint issues
pnpm lint:fix               # auto-fix eslint issues

pnpx codemod pnpm/catalog   # migrate dependencies to pnpm-workspace.yaml
```

## Other Notes

### Tanstack Router

The following is configured in [vite.config.ts](apps/web/vite.config.ts) web
application:

```ts
TanStackRouterVite({
  routeToken: 'layout',
}),
```

This enables the use of a `layout.tsx` file in each directory similar to NextJS.
You can read more about this
[here](https://github.com/TanStack/router/discussions/1102#discussioncomment-10946603).


## Pulumi Dev Flow

### First Time Setup
- Create a personal dev stack:
`pulumi stack init maive/<your-name>-dev --copy-config-from maive/infra/test`
- Commit the newly created `Pulumi.<your-name>-dev.yaml` file
- Package all the lambda functions
`cd maive/apps/backend`
`bash scripts/package_lambda.sh functions/{function_name}` <- do this for all functions in the functions dir
- In the `infra/` directory, run `pulumi up -y` 
- Manually create a style in the AWS cognito GUI for our managed login page
- Get vars in console for the next step 
`pulumi stack output --show-secrets `   
- Set env vars in `apps/web/.env` and `apps/server/.env`
- In the root directory, run `pnpm dev'`
-- You should get hot reloads for any frontend or server changes
- Sign up for a user account, verify email, and setup MFA

### Each subsequent time
- If `Pulumi.test.yaml` contains config changes or secrets not present in your stack's config, then you must copy them over
-- `pulumi stack select test && pulumi config cp --dest <your-name>-dev`
-- Must manually copy secrets via `pulumi config get my:key` and `pulumi config set my:key` (these are encrypted per stack)
- Any change to a lambda function means you need to rerun `bash scripts/package_lambda.sh functions/{function_name}`
- Other changes need to be redeployed with `pulumi up -y`
- Login to the site using your previously setup credentials
- Any long-standing config changes should be added to `Pulumi.test.yaml` and committed

### Other tips
- Follow logs via `pulumi logs --follow` in `infra/` folder

### Running local dev with containers
- Set the vars in `apps/server/.env` and `apps/web/.env`
- From the root of the project, run: `set -a && source ./apps/web/.env && set +a && docker compose up --build`