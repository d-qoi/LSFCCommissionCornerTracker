import { Tabs } from '@ark-ui/solid';
import { useQuery } from '@tanstack/solid-query';
import { createFileRoute, useNavigate } from '@tanstack/solid-router'
import { For, Suspense, Show } from 'solid-js';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/table';
import { fetchAllEvents, EventsData, EventTimeWhen } from '@/api/events';

export const Route = createFileRoute('/events')({
  component: RouteComponent,
})

const EventList = (props: { when: EventTimeWhen }) => {
  const query = useQuery(() => ({
    queryKey: ['events'],
    queryFn: fetchAllEvents,
  }));

  const navigate = useNavigate({ from: '/events' });

  return (
    <Suspense fallback={<div class="text-center py-8 text-gray-500 dark:text-gray-400">Loading Events...</div>}>
      <Show
        when={query.data && query.data[props.when as keyof EventsData].length > 0}
        fallback={
          <div class="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
            <div class="text-gray-400 dark:text-gray-500 mb-4">
              <svg class="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mb-2">
              No {props.when.toLowerCase()} events found
            </h3>
            <p class="text-gray-600 dark:text-gray-400 mb-4">
              Ready to get started?
            </p>
            <a
              href="/create-event"
              class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Create your first event
            </a>
          </div>
        }
      >
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event</TableHead>
                <TableHead>Opens</TableHead>
                <TableHead>Closes</TableHead>
                <TableHead>Seats</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <For each={query.data?.[props.when as keyof EventsData]}>
                {(event) => (
                  <TableRow
                    class="cursor-pointer"
                    onClick={() => navigate({ to: '/events/$eventId', params: { eventId: event.slug }, search: {artist: ""} })}
                  >
                    <TableCell class="font-medium text-gray-800 dark:text-gray-200">{event.name}</TableCell>
                    <TableCell class="text-gray-600 dark:text-gray-400">{event.startDate}</TableCell>
                    <TableCell class="text-gray-600 dark:text-gray-400">{event.endDate}</TableCell>
                    <TableCell>
                      <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        {event.seats} seats
                      </span>
                    </TableCell>
                  </TableRow>
                )}
              </For>
            </TableBody>
          </Table>
        </div>
      </Show>
    </Suspense>
  )
};

function RouteComponent() {
  return (
    <div class="max-w-6xl mx-auto px-4 py-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-800 dark:text-gray-200 mb-2">Events</h1>
        <p class="text-gray-600 dark:text-gray-400">Browse current, upcoming, and past commission events</p>
      </div>

      <Tabs.Root defaultValue="current" class="w-full">
        <Tabs.List class="flex space-x-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg mb-6">
          <Tabs.Trigger
            value={EventTimeWhen.CURRENT}
            class="flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors"
          >
            Current Events
          </Tabs.Trigger>
          <Tabs.Trigger
            value={EventTimeWhen.UPCOMING}
            class="flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors"
          >
            Upcoming Events
          </Tabs.Trigger>
          <Tabs.Trigger
            value={EventTimeWhen.PAST}
            class="flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors"
          >
            Past Events
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="current">
          <EventList when={EventTimeWhen.CURRENT} />
        </Tabs.Content>
        <Tabs.Content value="upcoming">
          <EventList when={EventTimeWhen.UPCOMING} />
        </Tabs.Content>
        <Tabs.Content value="past">
          <EventList when={EventTimeWhen.PAST} />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
