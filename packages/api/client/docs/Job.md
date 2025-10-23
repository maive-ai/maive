# Job

Universal job model that works across all CRM providers.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Unique job identifier (provider-specific format) | [default to undefined]
**name** | **string** |  | [optional] [default to undefined]
**number** | **string** |  | [optional] [default to undefined]
**status** | **string** | Current job status (provider-specific) | [default to undefined]
**status_id** | [**StatusId**](StatusId.md) |  | [optional] [default to undefined]
**workflow_type** | **string** |  | [optional] [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**customer_id** | **string** |  | [optional] [default to undefined]
**customer_name** | **string** |  | [optional] [default to undefined]
**address_line1** | **string** |  | [optional] [default to undefined]
**address_line2** | **string** |  | [optional] [default to undefined]
**city** | **string** |  | [optional] [default to undefined]
**state** | **string** |  | [optional] [default to undefined]
**postal_code** | **string** |  | [optional] [default to undefined]
**country** | **string** |  | [optional] [default to undefined]
**created_at** | **string** |  | [optional] [default to undefined]
**updated_at** | **string** |  | [optional] [default to undefined]
**completed_at** | **string** |  | [optional] [default to undefined]
**sales_rep_id** | **string** |  | [optional] [default to undefined]
**sales_rep_name** | **string** |  | [optional] [default to undefined]
**provider** | [**CRMProvider**](CRMProvider.md) | CRM provider name | [default to undefined]
**provider_data** | **{ [key: string]: any; }** | Provider-specific data | [optional] [default to undefined]

## Example

```typescript
import { Job } from './api';

const instance: Job = {
    id,
    name,
    number,
    status,
    status_id,
    workflow_type,
    description,
    customer_id,
    customer_name,
    address_line1,
    address_line2,
    city,
    state,
    postal_code,
    country,
    created_at,
    updated_at,
    completed_at,
    sales_rep_id,
    sales_rep_name,
    provider,
    provider_data,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
