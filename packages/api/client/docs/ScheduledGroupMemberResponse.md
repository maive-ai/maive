# ScheduledGroupMemberResponse

Response model for a single scheduled group member.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | Database ID of the member | [default to undefined]
**group_id** | **number** | Group ID | [default to undefined]
**project_id** | **string** | Project/Job ID from CRM | [default to undefined]
**goal_completed** | **boolean** | Whether the goal has been completed | [default to undefined]
**goal_completed_at** | **string** |  | [optional] [default to undefined]
**added_at** | **string** | When the project was added to the group | [default to undefined]

## Example

```typescript
import { ScheduledGroupMemberResponse } from './api';

const instance: ScheduledGroupMemberResponse = {
    id,
    group_id,
    project_id,
    goal_completed,
    goal_completed_at,
    added_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
