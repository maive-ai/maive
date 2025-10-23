# Note

Universal note/activity model that works across all CRM providers.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [optional] [default to undefined]
**text** | **string** | Note text content | [default to undefined]
**entity_id** | **string** | ID of the entity this note belongs to | [default to undefined]
**entity_type** | **string** | Type of entity (job, contact, project, etc.) | [default to undefined]
**created_by_id** | **string** |  | [optional] [default to undefined]
**created_by_name** | **string** |  | [optional] [default to undefined]
**created_at** | **string** | Creation timestamp (ISO format) | [default to undefined]
**updated_at** | **string** |  | [optional] [default to undefined]
**is_pinned** | **boolean** | Whether the note is pinned | [optional] [default to false]
**provider** | [**CRMProvider**](CRMProvider.md) | CRM provider name | [default to undefined]
**provider_data** | **{ [key: string]: any; }** | Provider-specific data | [optional] [default to undefined]

## Example

```typescript
import { Note } from './api';

const instance: Note = {
    id,
    text,
    entity_id,
    entity_type,
    created_by_id,
    created_by_name,
    created_at,
    updated_at,
    is_pinned,
    provider,
    provider_data,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
