# Contact

Universal contact/customer model that works across all CRM providers.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Unique contact identifier (provider-specific format) | [default to undefined]
**first_name** | **string** |  | [optional] [default to undefined]
**last_name** | **string** |  | [optional] [default to undefined]
**company** | **string** |  | [optional] [default to undefined]
**display_name** | **string** |  | [optional] [default to undefined]
**email** | **string** |  | [optional] [default to undefined]
**phone** | **string** |  | [optional] [default to undefined]
**mobile_phone** | **string** |  | [optional] [default to undefined]
**work_phone** | **string** |  | [optional] [default to undefined]
**address_line1** | **string** |  | [optional] [default to undefined]
**address_line2** | **string** |  | [optional] [default to undefined]
**city** | **string** |  | [optional] [default to undefined]
**state** | **string** |  | [optional] [default to undefined]
**postal_code** | **string** |  | [optional] [default to undefined]
**country** | **string** |  | [optional] [default to undefined]
**status** | **string** |  | [optional] [default to undefined]
**workflow_type** | **string** |  | [optional] [default to undefined]
**created_at** | **string** |  | [optional] [default to undefined]
**updated_at** | **string** |  | [optional] [default to undefined]
**provider** | [**CRMProvider**](CRMProvider.md) | CRM provider name | [default to undefined]
**provider_data** | **{ [key: string]: any; }** | Provider-specific data | [optional] [default to undefined]

## Example

```typescript
import { Contact } from './api';

const instance: Contact = {
    id,
    first_name,
    last_name,
    company,
    display_name,
    email,
    phone,
    mobile_phone,
    work_phone,
    address_line1,
    address_line2,
    city,
    state,
    postal_code,
    country,
    status,
    workflow_type,
    created_at,
    updated_at,
    provider,
    provider_data,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
