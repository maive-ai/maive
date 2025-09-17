# AuthenticationApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getCurrentUserInfoApiAuthMeGet**](#getcurrentuserinfoapiauthmeget) | **GET** /api/auth/me | Get Current User Info|
|[**oauthCallbackApiAuthCallbackGet**](#oauthcallbackapiauthcallbackget) | **GET** /api/auth/callback | Oauth Callback|
|[**refreshTokenApiAuthRefreshPost**](#refreshtokenapiauthrefreshpost) | **POST** /api/auth/refresh | Refresh Token|
|[**signOutApiAuthSignoutPost**](#signoutapiauthsignoutpost) | **POST** /api/auth/signout | Sign Out|

# **getCurrentUserInfoApiAuthMeGet**
> User getCurrentUserInfoApiAuthMeGet()

Get current user information.  Returns the profile information of the currently authenticated user.

### Example

```typescript
import {
    AuthenticationApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AuthenticationApi(configuration);

const { status, data } = await apiInstance.getCurrentUserInfoApiAuthMeGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**User**

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **oauthCallbackApiAuthCallbackGet**
> any oauthCallbackApiAuthCallbackGet()

OAuth2 callback endpoint for Cognito authentication.  Exchanges authorization code for tokens and redirects to frontend.

### Example

```typescript
import {
    AuthenticationApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AuthenticationApi(configuration);

let code: string; // (optional) (default to undefined)
let error: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.oauthCallbackApiAuthCallbackGet(
    code,
    error
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **code** | [**string**] |  | (optional) defaults to undefined|
| **error** | [**string**] |  | (optional) defaults to undefined|


### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **refreshTokenApiAuthRefreshPost**
> AuthResponse refreshTokenApiAuthRefreshPost()

Refresh access token using refresh token.  Uses the refresh token from cookies to get a new access token.

### Example

```typescript
import {
    AuthenticationApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AuthenticationApi(configuration);

const { status, data } = await apiInstance.refreshTokenApiAuthRefreshPost();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**AuthResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **signOutApiAuthSignoutPost**
> any signOutApiAuthSignoutPost()

Sign out the current user.  Invalidates the current user\'s session and clears cookies.

### Example

```typescript
import {
    AuthenticationApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AuthenticationApi(configuration);

const { status, data } = await apiInstance.signOutApiAuthSignoutPost();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**any**

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

