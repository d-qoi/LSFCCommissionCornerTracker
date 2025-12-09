import { Collapsible } from '@ark-ui/solid';
import { QueryClient, QueryClientProvider } from '@tanstack/solid-query';
import { Link, Outlet, createRootRoute } from '@tanstack/solid-router';
import { TanStackRouterDevtools } from '@tanstack/solid-router-devtools';
import { SolidQueryDevtools } from '@tanstack/solid-query-devtools'

export const Route = createRootRoute({
  component: RootComponent,
  notFoundComponent: () => {
    return (
      <div class="flex flex-col items-center justify-center min-h-screen bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200">
        <h1 class="text-2xl font-bold mb-4">Page Not Found</h1>
        <p class="text-gray-600 dark:text-gray-400 mb-6">This page doesn't exist.</p>
        <Link
          to="/"
          class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          Go Home
        </Link>
      </div>
    );
  },
});

const queryClient = new QueryClient();

function RootComponent() {

  return (
    <>
      <header class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <Collapsible.Root defaultOpen class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div class="flex items-center justify-between h-16">
            <Collapsible.Trigger class="text-lg font-semibold text-gray-800 dark:text-gray-200 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
              LSFC Commission Corner
            </Collapsible.Trigger>

            <Collapsible.Content class="flex-1 ml-8">
              <div class="flex justify-between items-center">
                <nav class="flex space-x-6">
                  <Link
                    to="/"
                    class="nav-link"
                    activeProps={{ class: 'nav-link active' }}
                    activeOptions={{ exact: true }}
                  >
                    Home
                  </Link>
                  <Link
                    to="/events"
                    class="nav-link"
                    activeProps={{ class: 'nav-link active' }}
                  >
                    Events
                  </Link>
                  <Link
                    to="/profile"
                    class="nav-link"
                    activeProps={{ class: 'nav-link active' }}
                  >
                    My Profile
                  </Link>
                </nav>

                <div class="flex space-x-4">
                  <Link
                    to="/login"
                    class="nav-link"
                    activeProps={{ class: 'nav-link active' }}
                  >
                    Login
                  </Link>
                  <Link
                    to="/logout"
                    class="nav-link"
                    activeProps={{ class: 'nav-link active' }}
                  >
                    Logout
                  </Link>
                </div>
              </div>
            </Collapsible.Content>
          </div>
        </Collapsible.Root>
      </header>

      <main class="min-h-screen bg-gray-50 dark:bg-gray-900">
        <QueryClientProvider client={queryClient}>
          <Outlet />
          <SolidQueryDevtools buttonPosition="bottom-left" />
        </QueryClientProvider>
      </main>

      <TanStackRouterDevtools position="bottom-right" />
    </>
  );
}
