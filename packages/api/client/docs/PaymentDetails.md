# PaymentDetails

Provider-agnostic payment information from claim status calls.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **string** |  | [optional] [default to undefined]
**amount** | **number** |  | [optional] [default to undefined]
**issue_date** | **string** |  | [optional] [default to undefined]
**check_number** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { PaymentDetails } from './api';

const instance: PaymentDetails = {
    status,
    amount,
    issue_date,
    check_number,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
