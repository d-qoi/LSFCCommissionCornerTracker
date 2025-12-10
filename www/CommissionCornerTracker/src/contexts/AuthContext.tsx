// src/contexts/AuthContext.tsx
import { createContext, useContext, createSignal, onMount, JSX } from 'solid-js'
import Keycloak from 'keycloak-js'

interface AuthContextType {
    keycloak: Keycloak | null
    isAuthenticated: () => boolean
    login: () => void
    logout: () => void
    token: () => string | null
}

const AuthContext = createContext<AuthContextType>()

export function AuthProvider(props: { children: JSX.Element }) {
    const [keycloak, setKeycloak] = createSignal<Keycloak | null>(null)
    const [isAuthenticated, setIsAuthenticated] = createSignal(false)
    const [token, setToken] = createSignal<string | null>(null)

    onMount(async () => {
        // Fetch config from your FastAPI backend
        const config = await fetch('/api/auth/config').then(r => r.json())

        const kc = new Keycloak({
            url: config.server_url,
            realm: config.realm,
            clientId: config.client_id
        })

        try {
            const authenticated = await kc.init({ onLoad: 'check-sso' })
            setKeycloak(kc)
            setIsAuthenticated(authenticated)
            if (authenticated) {
                setToken(kc.token!)
            }
        } catch (error) {
            console.error('Keycloak init failed:', error)
        }
    })

    const login = () => keycloak()?.login()
    const logout = () => keycloak()?.logout()

    return (
        <AuthContext.Provider value={{
            keycloak: keycloak(),
            isAuthenticated,
            login,
            logout,
            token
        }}>
            {props.children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => useContext(AuthContext)!
