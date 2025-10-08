# CallRequest

Request model for creating an outbound call.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**phone_number** | **string** | Phone number to call | [default to undefined]
**customer_id** | **string** |  | [optional] [default to undefined]
**customer_name** | **string** |  | [optional] [default to undefined]
**company_name** | **string** |  | [optional] [default to undefined]
**customer_address** | **string** |  | [optional] [default to undefined]
**claim_number** | **string** |  | [optional] [default to undefined]
**date_of_loss** | **string** |  | [optional] [default to undefined]
**insurance_agency** | **string** |  | [optional] [default to undefined]
**adjuster_name** | **string** |  | [optional] [default to undefined]
**adjuster_phone** | **string** |  | [optional] [default to undefined]
**metadata** | **{ [key: string]: any; }** | Additional metadata | [optional] [default to undefined]
**job_id** | **number** |  | [optional] [default to undefined]
**tenant** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { CallRequest } from './api';

const instance: CallRequest = {
    phone_number,
    customer_id,
    customer_name,
    company_name,
    customer_address,
    claim_number,
    date_of_loss,
    insurance_agency,
    adjuster_name,
    adjuster_phone,
    metadata,
    job_id,
    tenant,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
