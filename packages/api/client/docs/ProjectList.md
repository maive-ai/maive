# ProjectList

Universal project list response with pagination.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**projects** | [**Array&lt;SrcIntegrationsCrmSchemasProject2&gt;**](SrcIntegrationsCrmSchemasProject2.md) | List of projects | [default to undefined]
**total_count** | **number** | Total number of projects | [default to undefined]
**provider** | [**CRMProvider**](CRMProvider.md) | CRM provider name | [default to undefined]
**page** | **number** |  | [optional] [default to undefined]
**page_size** | **number** |  | [optional] [default to undefined]
**has_more** | **boolean** |  | [optional] [default to undefined]

## Example

```typescript
import { ProjectList } from './api';

const instance: ProjectList = {
    projects,
    total_count,
    provider,
    page,
    page_size,
    has_more,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
