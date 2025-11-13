# CreateScheduledGroupRequest

Request model for creating a scheduled group.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** | Group display name | [default to undefined]
**frequency** | **Array&lt;string&gt;** | Days of week: [\&#39;monday\&#39;, \&#39;tuesday\&#39;, etc.] | [default to undefined]
**time_of_day** | **string** | Time of day to make calls | [default to undefined]
**goal_type** | [**GoalType**](GoalType.md) | Type of goal for this group | [default to undefined]
**goal_description** | **string** |  | [optional] [default to undefined]
**who_to_call** | [**WhoToCall**](WhoToCall.md) | Who to call for this group | [default to undefined]

## Example

```typescript
import { CreateScheduledGroupRequest } from './api';

const instance: CreateScheduledGroupRequest = {
    name,
    frequency,
    time_of_day,
    goal_type,
    goal_description,
    who_to_call,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
