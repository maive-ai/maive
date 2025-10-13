# ClaimStatusData

Provider-agnostic structured data from insurance claim status calls.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**call_outcome** | **string** | Call outcome: success, voicemail, gatekeeper, failed | [optional] [default to 'unknown']
**claim_status** | [**ClaimStatus**](ClaimStatus.md) | Claim status: approved, denied, pending_review, etc. | [optional] [default to undefined]
**payment_details** | [**PaymentDetails**](PaymentDetails.md) |  | [optional] [default to undefined]
**required_actions** | [**RequiredActions**](RequiredActions.md) |  | [optional] [default to undefined]
**claim_update_summary** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { ClaimStatusData } from './api';

const instance: ClaimStatusData = {
    call_outcome,
    claim_status,
    payment_details,
    required_actions,
    claim_update_summary,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
