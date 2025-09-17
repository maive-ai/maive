# User

User information.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** | User\&#39;s unique identifier | [default to undefined]
**email** | **string** | User\&#39;s email address | [default to undefined]
**name** | **string** |  | [optional] [default to undefined]
**role** | [**Role**](Role.md) |  | [optional] [default to undefined]
**organization_id** | **string** |  | [optional] [default to undefined]
**profile_picture** | **string** |  | [optional] [default to undefined]
**email_verified** | **boolean** | Whether user\&#39;s email is verified | [optional] [default to false]
**mfa_enabled** | **boolean** | Whether MFA is enabled for the user | [optional] [default to false]
**created_at** | **string** |  | [optional] [default to undefined]
**updated_at** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { User } from './api';

const instance: User = {
    id,
    email,
    name,
    role,
    organization_id,
    profile_picture,
    email_verified,
    mfa_enabled,
    created_at,
    updated_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
