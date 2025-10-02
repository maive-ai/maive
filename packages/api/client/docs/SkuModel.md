# SkuModel

SKU model for estimate items.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | SKU ID | [default to undefined]
**name** | **string** | SKU name | [default to undefined]
**displayName** | **string** | Display name | [default to undefined]
**type** | **string** | SKU type | [default to undefined]
**soldHours** | **number** | Sold hours | [default to undefined]
**generalLedgerAccountId** | **number** | General ledger account ID | [default to undefined]
**generalLedgerAccountName** | **string** | General ledger account name | [default to undefined]
**modifiedOn** | **string** | Date/time (in UTC) when SKU was last modified | [default to undefined]

## Example

```typescript
import { SkuModel } from './api';

const instance: SkuModel = {
    id,
    name,
    displayName,
    type,
    soldHours,
    generalLedgerAccountId,
    generalLedgerAccountName,
    modifiedOn,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
