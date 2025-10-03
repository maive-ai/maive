# JobNoteResponse

Response model for job note.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**text** | **string** | Text content of the note | [default to undefined]
**isPinned** | **boolean** | Whether the note is pinned to the top | [default to undefined]
**createdById** | **number** | ID of user who created this note | [default to undefined]
**createdOn** | **string** | Date/time (in UTC) the note was created | [default to undefined]
**modifiedOn** | **string** | Date/time (in UTC) the note was modified | [default to undefined]

## Example

```typescript
import { JobNoteResponse } from './api';

const instance: JobNoteResponse = {
    text,
    isPinned,
    createdById,
    createdOn,
    modifiedOn,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
