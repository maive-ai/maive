# ProjectData

Mock project data model with all customer and claim information.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | Project ID | [default to undefined]
**customerName** | **string** | Customer/homeowner name | [default to undefined]
**address** | **string** | Property address | [default to undefined]
**phone** | **string** | Customer phone number | [default to undefined]
**email** | **string** |  | [optional] [default to undefined]
**claimNumber** | **string** |  | [optional] [default to undefined]
**dateOfLoss** | **string** |  | [optional] [default to undefined]
**insuranceAgency** | **string** |  | [optional] [default to undefined]
**insuranceAgencyContact** | [**ContactInfo**](ContactInfo.md) |  | [optional] [default to undefined]
**adjusterName** | **string** |  | [optional] [default to undefined]
**adjusterContact** | [**ContactInfo**](ContactInfo.md) |  | [optional] [default to undefined]
**notes** | **string** |  | [optional] [default to undefined]
**tenant** | **number** |  | [optional] [default to undefined]
**job_id** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { ProjectData } from './api';

const instance: ProjectData = {
    id,
    customerName,
    address,
    phone,
    email,
    claimNumber,
    dateOfLoss,
    insuranceAgency,
    insuranceAgencyContact,
    adjusterName,
    adjusterContact,
    notes,
    tenant,
    job_id,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
