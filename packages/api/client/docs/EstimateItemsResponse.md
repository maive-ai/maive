# EstimateItemsResponse

Response model for estimate items list.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**items** | [**Array&lt;EstimateItemResponse&gt;**](EstimateItemResponse.md) | List of estimate items | [default to undefined]
**total_count** | **number** |  | [optional] [default to undefined]
**page** | **number** | Current page number | [default to undefined]
**page_size** | **number** | Page size | [default to undefined]
**has_more** | **boolean** | Whether there are more items | [default to undefined]

## Example

```typescript
import { EstimateItemsResponse } from './api';

const instance: EstimateItemsResponse = {
    items,
    total_count,
    page,
    page_size,
    has_more,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
