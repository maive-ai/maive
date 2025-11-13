# UpdateScheduledGroupRequest

Request model for updating a scheduled group.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [optional] [default to undefined]
**frequency** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**time_of_day** | **string** |  | [optional] [default to undefined]
**goal_type** | [**GoalType**](GoalType.md) |  | [optional] [default to undefined]
**goal_description** | **string** |  | [optional] [default to undefined]
**who_to_call** | [**WhoToCall**](WhoToCall.md) |  | [optional] [default to undefined]

## Example

```typescript
import { UpdateScheduledGroupRequest } from './api';

const instance: UpdateScheduledGroupRequest = {
    name,
    frequency,
    time_of_day,
    goal_type,
    goal_description,
    who_to_call,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
