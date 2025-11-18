# CRMCredentialsCreate

Schema for creating CRM credentials.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**provider** | **string** | CRM provider (job_nimbus, service_titan) | [default to undefined]
**credentials** | **{ [key: string]: any; }** | CRM API credentials (will be encrypted) | [default to undefined]

## Example

```typescript
import { CRMCredentialsCreate } from './api';

const instance: CRMCredentialsCreate = {
    provider,
    credentials,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
