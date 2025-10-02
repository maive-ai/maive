# EstimateItemResponse

Response model for estimate item information.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | ID of the estimate item | [default to undefined]
**sku** | [**SkuModel**](SkuModel.md) | SKU details | [default to undefined]
**skuAccount** | **string** | SKU account | [default to undefined]
**description** | **string** | Item description | [default to undefined]
**membershipTypeId** | **number** |  | [optional] [default to undefined]
**qty** | **number** | Quantity | [default to undefined]
**unitRate** | **number** | Unit rate | [default to undefined]
**total** | **number** | Total amount | [default to undefined]
**unitCost** | **number** | Unit cost | [default to undefined]
**totalCost** | **number** | Total cost | [default to undefined]
**itemGroupName** | **string** |  | [optional] [default to undefined]
**itemGroupRootId** | **number** |  | [optional] [default to undefined]
**createdOn** | **string** | Date/time (in UTC) when the item was created | [default to undefined]
**modifiedOn** | **string** | Date/time (in UTC) when the item was last modified | [default to undefined]
**chargeable** | **boolean** |  | [optional] [default to undefined]
**invoiceItemId** | **number** |  | [optional] [default to undefined]
**budgetCodeId** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { EstimateItemResponse } from './api';

const instance: EstimateItemResponse = {
    id,
    sku,
    skuAccount,
    description,
    membershipTypeId,
    qty,
    unitRate,
    total,
    unitCost,
    totalCost,
    itemGroupName,
    itemGroupRootId,
    createdOn,
    modifiedOn,
    chargeable,
    invoiceItemId,
    budgetCodeId,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
