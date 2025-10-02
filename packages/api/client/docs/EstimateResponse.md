# EstimateResponse

Response model for Service Titan estimate information.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | ID of the estimate | [default to undefined]
**jobId** | **number** |  | [optional] [default to undefined]
**projectId** | **number** |  | [optional] [default to undefined]
**locationId** | **number** |  | [optional] [default to undefined]
**customerId** | **number** |  | [optional] [default to undefined]
**name** | **string** |  | [optional] [default to undefined]
**jobNumber** | **string** |  | [optional] [default to undefined]
**status** | [**EstimateStatus**](EstimateStatus.md) |  | [optional] [default to undefined]
**reviewStatus** | [**EstimateReviewStatus**](EstimateReviewStatus.md) | Review status of the estimate | [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]
**createdOn** | **string** | Date/time (in UTC) when the estimate was created | [default to undefined]
**modifiedOn** | **string** | Date/time (in UTC) when estimate was last modified | [default to undefined]
**soldOn** | **string** |  | [optional] [default to undefined]
**soldBy** | **number** |  | [optional] [default to undefined]
**active** | **boolean** | Whether the estimate is active | [default to undefined]
**subtotal** | **number** | Subtotal amount | [default to undefined]
**tax** | **number** | Tax amount | [default to undefined]
**businessUnitId** | **number** |  | [optional] [default to undefined]
**businessUnitName** | **string** |  | [optional] [default to undefined]
**isRecommended** | **boolean** | Whether this estimate is recommended | [default to undefined]
**budgetCodeId** | **number** |  | [optional] [default to undefined]
**isChangeOrder** | **boolean** | Whether this estimate is a change order | [default to undefined]

## Example

```typescript
import { EstimateResponse } from './api';

const instance: EstimateResponse = {
    id,
    jobId,
    projectId,
    locationId,
    customerId,
    name,
    jobNumber,
    status,
    reviewStatus,
    summary,
    createdOn,
    modifiedOn,
    soldOn,
    soldBy,
    active,
    subtotal,
    tax,
    businessUnitId,
    businessUnitName,
    isRecommended,
    budgetCodeId,
    isChangeOrder,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
