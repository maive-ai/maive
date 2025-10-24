# ContactList

Universal contact list response with pagination.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**contacts** | [**Array&lt;Contact&gt;**](Contact.md) | List of contacts | [default to undefined]
**total_count** | **number** | Total number of contacts | [default to undefined]
**provider** | [**CRMProvider**](CRMProvider.md) | CRM provider name | [default to undefined]
**page** | **number** |  | [optional] [default to undefined]
**page_size** | **number** |  | [optional] [default to undefined]
**has_more** | **boolean** |  | [optional] [default to undefined]

## Example

```typescript
import { ContactList } from './api';

const instance: ContactList = {
    contacts,
    total_count,
    provider,
    page,
    page_size,
    has_more,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
