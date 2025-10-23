# Project

Universal project model that works across all CRM providers.  In hierarchical CRMs (Service Titan), projects are top-level containers that may contain multiple jobs. In flat CRMs (JobNimbus), projects and jobs are the same entity.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Unique project identifier (provider-specific format) | [default to undefined]
**name** | **string** |  | [optional] [default to undefined]
**number** | **string** |  | [optional] [default to undefined]
**status** | **string** | Current project status (provider-specific) | [default to undefined]
**status_id** | [**StatusId**](StatusId.md) |  | [optional] [default to undefined]
**sub_status** | **string** |  | [optional] [default to undefined]
**sub_status_id** | [**SubStatusId**](SubStatusId.md) |  | [optional] [default to undefined]
**workflow_type** | **string** |  | [optional] [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**customer_id** | **string** |  | [optional] [default to undefined]
**customer_name** | **string** |  | [optional] [default to undefined]
**location_id** | **string** |  | [optional] [default to undefined]
**address_line1** | **string** |  | [optional] [default to undefined]
**address_line2** | **string** |  | [optional] [default to undefined]
**city** | **string** |  | [optional] [default to undefined]
**state** | **string** |  | [optional] [default to undefined]
**postal_code** | **string** |  | [optional] [default to undefined]
**country** | **string** |  | [optional] [default to undefined]
**created_at** | **string** |  | [optional] [default to undefined]
**updated_at** | **string** |  | [optional] [default to undefined]
**start_date** | **string** |  | [optional] [default to undefined]
**target_completion_date** | **string** |  | [optional] [default to undefined]
**actual_completion_date** | **string** |  | [optional] [default to undefined]
**claim_number** | **string** |  | [optional] [default to undefined]
**date_of_loss** | **string** |  | [optional] [default to undefined]
**insurance_company** | **string** |  | [optional] [default to undefined]
**adjuster_name** | **string** |  | [optional] [default to undefined]
**adjuster_phone** | **string** |  | [optional] [default to undefined]
**adjuster_email** | **string** |  | [optional] [default to undefined]
**sales_rep_id** | **string** |  | [optional] [default to undefined]
**sales_rep_name** | **string** |  | [optional] [default to undefined]
**provider** | [**CRMProvider**](CRMProvider.md) | CRM provider name | [default to undefined]
**provider_data** | **{ [key: string]: any; }** | Provider-specific data | [optional] [default to undefined]

## Example

```typescript
import { Project } from './api';

const instance: Project = {
    id,
    name,
    number,
    status,
    status_id,
    sub_status,
    sub_status_id,
    workflow_type,
    description,
    customer_id,
    customer_name,
    location_id,
    address_line1,
    address_line2,
    city,
    state,
    postal_code,
    country,
    created_at,
    updated_at,
    start_date,
    target_completion_date,
    actual_completion_date,
    claim_number,
    date_of_loss,
    insurance_company,
    adjuster_name,
    adjuster_phone,
    adjuster_email,
    sales_rep_id,
    sales_rep_name,
    provider,
    provider_data,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
