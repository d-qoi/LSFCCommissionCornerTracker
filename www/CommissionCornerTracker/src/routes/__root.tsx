import { Collapsible, CollapsibleRoot } from '@ark-ui/solid';
import { QueryClient, QueryClientProvider } from '@tanstack/solid-query';
import { Link, Outlet, createRootRoute } from '@tanstack/solid-router';
import { TanStackRouterDevtools } from '@tanstack/solid-router-devtools';
import { SolidQueryDevtools } from '@tanstack/solid-query-devtools'

export const Route = createRootRoute({
  component: RootComponent,
  notFoundComponent: () => {
    return (
      <div>
        <p>This is the notFoundComponent configured on root route</p>
        <Link to="/">Start Over</Link>
      </div>
    );
  },
});

function RootComponent() {
  const queryClient = new QueryClient();

  return (
    <>
      <Collapsible.Root defaultOpen class="flex items-center gap-5 p-2 text-lg border-b width-full">
        <Collapsible.Trigger>
          Menu
        </Collapsible.Trigger>
        <Collapsible.Content class="flex-1">
          <div class="flex justify-between w-full">
            <div class="flex gap-5">
              <Link
                to="/"
                class='nav-link'
                activeProps={{
                  class: 'nav-link active',
                }}
                activeOptions={{ exact: true }}
              >
                Home
              </Link>{' '}
              <Link
                to="/events"
                class='nav-link'
                activeProps={{
                  class: 'nav-link active',
                }}
              >
                Events
              </Link>{' '}
              <Link
                to="/profile"
                class='nav-link'
                activeProps={{
                  class: 'nav-link active',
                }}
              >
                My Profile
              </Link>
            </div>
            <div class="flex gap-2">
              <Link
                to="/login"
                class='nav-link'
                activeProps={{
                  class: 'nav-link active',
                }}>
                Login
              </Link>
              <Link
                to="/logout"
                class='nav-link'
                activeProps={{
                  class: 'nav-link active',
                }}>
                Logout
              </Link>
            </div>
          </div>
        </Collapsible.Content>
      </Collapsible.Root>

      <div class="p-2 flex gap-2 text-lg border-b hidden">
        <Link
          to="/"
          activeProps={{
            class: 'font-bold',
          }}
          activeOptions={{ exact: true }}
        >
          Home
        </Link>{' '}
        <Link
          to="/posts"
          activeProps={{
            class: 'font-bold',
          }}
        >
          Posts
        </Link>{' '}
        <Link
          to="/layout-a"
          activeProps={{
            class: 'font-bold',
          }}
        >
          Layout
        </Link>{' '}
        <Link
          // @ts-expect-error
          to="/this-route-does-not-exist"
          activeProps={{
            class: 'font-bold',
          }}
        >
          This Route Does Not Exist
        </Link>
      </div>
      <hr />
      <QueryClientProvider client={queryClient}>
        <Outlet />
        <SolidQueryDevtools buttonPosition="bottom-left" />
      </QueryClientProvider>
      {/* Start rendering router matches */}
      <TanStackRouterDevtools position="bottom-right" />
    </>
  );
}
