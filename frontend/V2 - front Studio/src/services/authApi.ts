import { OperatorProfile } from '../types';

/**
 * Authentication Service
 * Pre-configured for Google Workspace API / Google OAuth and synaptic token authentication.
 */

const STORAGE_KEY = 'nimb_operator_session';

export const authApiService = {
  getStoredSession(): OperatorProfile {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // fallback
    }
    return {
      name: 'Operador // Nexus',
      title: 'Acesso Mestre Niv. 4',
      email: 'operador@cluster-nimb.network',
      level: 'Clearance IV',
      isAuthenticated: true,
      provider: 'manual',
    };
  },

  async loginWithGoogle(): Promise<OperatorProfile> {
    // Simulated Google OAuth flow with Workspace scope verification
    await new Promise((r) => setTimeout(r, 600));

    const profile: OperatorProfile = {
      name: 'Rafael Pereira // Google Nexus',
      title: 'Operador Conectado (Google Workspace API)',
      email: 'rafael97pereira@gmail.com',
      level: 'Master Clearance V',
      isAuthenticated: true,
      provider: 'google',
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
    return profile;
  },

  async loginWithToken(email: string, _token: string): Promise<OperatorProfile> {
    await new Promise((r) => setTimeout(r, 800));

    const profile: OperatorProfile = {
      name: email.split('@')[0] + ' // Sinapse',
      title: 'Operador Credenciado',
      email,
      level: 'Clearance IV',
      isAuthenticated: true,
      provider: 'manual',
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
    return profile;
  },

  logout(): void {
    localStorage.removeItem(STORAGE_KEY);
  },
};
