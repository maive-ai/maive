# JobResponse

Response model for Service Titan job information.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | ID of the job | [default to undefined]
**jobNumber** | **string** | Job number | [default to undefined]
**projectId** | **number** |  | [optional] [default to undefined]
**customerId** | **number** | ID of the job\&#39;s customer | [default to undefined]
**locationId** | **number** | ID of the job\&#39;s location | [default to undefined]
**jobStatus** | **string** | Status of the job | [default to undefined]
**completedOn** | **string** |  | [optional] [default to undefined]
**businessUnitId** | **number** | ID of the job\&#39;s business unit | [default to undefined]
**jobTypeId** | **number** | ID of job type | [default to undefined]
**priority** | **string** | Priority of the job | [default to undefined]
**campaignId** | **number** | ID of the job\&#39;s campaign | [default to undefined]
**appointmentCount** | **number** | Number of appointments on the job | [default to undefined]
**firstAppointmentId** | **number** | ID of the first appointment on the job | [default to undefined]
**lastAppointmentId** | **number** | ID of the last appointment on the job | [default to undefined]
**recallForId** | **number** |  | [optional] [default to undefined]
**warrantyId** | **number** |  | [optional] [default to undefined]
**noCharge** | **boolean** | Whether the job is a no-charge job | [default to undefined]
**notificationsEnabled** | **boolean** | Whether notifications will be sent to customers | [default to undefined]
**createdOn** | **string** | Date/time (in UTC) when the job was created | [default to undefined]
**createdById** | **number** | ID of the user who created the job | [default to undefined]
**modifiedOn** | **string** | Date/time (in UTC) when job was last modified | [default to undefined]
**tagTypeIds** | **Array&lt;number&gt;** | Tags on the job | [default to undefined]
**customerPo** | **string** |  | [optional] [default to undefined]
**invoiceId** | **number** |  | [optional] [default to undefined]
**total** | **number** |  | [optional] [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { JobResponse } from './api';

const instance: JobResponse = {
    id,
    jobNumber,
    projectId,
    customerId,
    locationId,
    jobStatus,
    completedOn,
    businessUnitId,
    jobTypeId,
    priority,
    campaignId,
    appointmentCount,
    firstAppointmentId,
    lastAppointmentId,
    recallForId,
    warrantyId,
    noCharge,
    notificationsEnabled,
    createdOn,
    createdById,
    modifiedOn,
    tagTypeIds,
    customerPo,
    invoiceId,
    total,
    summary,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
