# ScheduledGroupResponse

Response model for a scheduled group.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | Database ID of the group | [default to undefined]
**user_id** | **string** | Cognito user ID | [default to undefined]
**name** | **string** | Group display name | [default to undefined]
**frequency** | **Array&lt;string&gt;** | Days of week | [default to undefined]
**time_of_day** | **string** | Time of day (HH:MM:SS format) | [default to undefined]
**goal_type** | **string** | Goal type | [default to undefined]
**goal_description** | **string** |  | [optional] [default to undefined]
**who_to_call** | **string** | Who to call | [default to undefined]
**is_active** | **boolean** | Whether the group is active | [default to undefined]
**member_count** | **number** | Number of projects in the group | [default to undefined]
**created_at** | **string** | When the group was created | [default to undefined]
**updated_at** | **string** | When the group was last updated | [default to undefined]

## Example

```typescript
import { ScheduledGroupResponse } from './api';

const instance: ScheduledGroupResponse = {
    id,
    user_id,
    name,
    frequency,
    time_of_day,
    goal_type,
    goal_description,
    who_to_call,
    is_active,
    member_count,
    created_at,
    updated_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
