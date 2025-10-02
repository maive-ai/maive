# ProjectStatusResponse

Response model for project status information.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**project_id** | **string** | Unique project identifier | [default to undefined]
**status** | [**Status**](Status.md) | Current project status | [default to undefined]
**provider** | [**CRMProvider**](CRMProvider.md) | CRM provider | [default to undefined]
**updated_at** | **string** |  | [optional] [default to undefined]
**provider_data** | **{ [key: string]: any; }** |  | [optional] [default to undefined]

## Example

```typescript
import { ProjectStatusResponse } from './api';

const instance: ProjectStatusResponse = {
    project_id,
    status,
    provider,
    updated_at,
    provider_data,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
