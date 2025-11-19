# MockProject

Mock project data model (Mock CRM only).

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [optional] [default to undefined]
**customerName** | **string** | Customer name | [default to undefined]
**address** | **string** |  | [optional] [default to undefined]
**phone** | **string** |  | [optional] [default to undefined]
**email** | **string** |  | [optional] [default to undefined]
**claimNumber** | **string** |  | [optional] [default to undefined]
**dateOfLoss** | **string** |  | [optional] [default to undefined]
**insuranceCompany** | **string** |  | [optional] [default to undefined]
**insuranceAgency** | **string** |  | [optional] [default to undefined]
**insuranceAgencyContact** | [**ContactInfo**](ContactInfo.md) |  | [optional] [default to undefined]
**insuranceContactName** | **string** |  | [optional] [default to undefined]
**insuranceContactPhone** | **string** |  | [optional] [default to undefined]
**insuranceContactEmail** | **string** |  | [optional] [default to undefined]
**adjusterName** | **string** |  | [optional] [default to undefined]
**adjusterContact** | [**ContactInfo**](ContactInfo.md) |  | [optional] [default to undefined]
**adjusterContactName** | **string** |  | [optional] [default to undefined]
**adjusterContactPhone** | **string** |  | [optional] [default to undefined]
**adjusterContactEmail** | **string** |  | [optional] [default to undefined]
**notes** | [**Array&lt;MockNote&gt;**](MockNote.md) |  | [optional] [default to undefined]
**status** | **string** | Project status | [optional] [default to 'In Progress']

## Example

```typescript
import { MockProject } from './api';

const instance: MockProject = {
    id,
    customerName,
    address,
    phone,
    email,
    claimNumber,
    dateOfLoss,
    insuranceCompany,
    insuranceAgency,
    insuranceAgencyContact,
    insuranceContactName,
    insuranceContactPhone,
    insuranceContactEmail,
    adjusterName,
    adjusterContact,
    adjusterContactName,
    adjusterContactPhone,
    adjusterContactEmail,
    notes,
    status,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
