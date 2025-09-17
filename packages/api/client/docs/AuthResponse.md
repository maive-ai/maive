# AuthResponse

Schema for authentication responses.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**success** | **boolean** | Whether the operation was successful | [default to undefined]
**session** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**error** | **string** |  | [optional] [default to undefined]
**requires_mfa** | **boolean** | Whether MFA is required | [optional] [default to false]
**mfa_setup_required** | **boolean** | Whether MFA setup is required | [optional] [default to false]

## Example

```typescript
import { AuthResponse } from './api';

const instance: AuthResponse = {
    success,
    session,
    error,
    requires_mfa,
    mfa_setup_required,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
