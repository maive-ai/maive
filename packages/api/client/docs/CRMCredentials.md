# CRMCredentials

CRM credentials schema with full details (no actual credentials exposed).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**provider** | **string** | CRM provider (job_nimbus, service_titan) | [default to undefined]
**id** | **string** | Credential record UUID | [default to undefined]
**organization_id** | **string** | Organization UUID | [default to undefined]
**secret_arn** | **string** | AWS Secrets Manager ARN | [default to undefined]
**is_active** | **boolean** | Whether credentials are active | [default to undefined]
**created_by** | **string** | User who created the credentials | [default to undefined]
**created_at** | **string** | Creation timestamp | [default to undefined]
**updated_at** | **string** | Last update timestamp | [default to undefined]

## Example

```typescript
import { CRMCredentials } from './api';

const instance: CRMCredentials = {
    provider,
    id,
    organization_id,
    secret_arn,
    is_active,
    created_by,
    created_at,
    updated_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
