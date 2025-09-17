import { AuthenticationApi, Configuration, type User } from '@maive/api/client';
import { env } from '../env';

const config = new Configuration({
  basePath: env.PUBLIC_SERVER_URL,
  baseOptions: { withCredentials: true },
});

const authApi = new AuthenticationApi(config);

export async function getCurrentUser(): Promise<User | null> {
  try {
    const response = await authApi.getCurrentUserInfoApiAuthMeGet();
    return response.data;
  } catch {
    return null;
  }
}

export async function signOut(): Promise<void> {
  await authApi.signOutApiAuthSignoutPost();
}
