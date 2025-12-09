import { TabList, Tabs, TabsContext, TabsRoot } from '@ark-ui/solid';
import { useQuery } from '@tanstack/solid-query';
import { createFileRoute, Link, useNavigate } from '@tanstack/solid-router'
import { For, Suspense, Switch, Match, Show } from 'solid-js';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/table';
import { fetchAllEvents, EventsData, EventTimeWhen } from '../api/events';

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
    <Suspense fallback={<>Loading Events...</>}>
      <Show
        when={query.data && query.data[props.when as keyof EventsData].length > 0}
        fallback={
          <div class="text-center py-8">
            <p class="text-gray-600 mb-2">No {props.when.toLowerCase()} events found!</p>
            <p class="text-sm text-gray-500">
              Ready to get started? <a href="/create-event" class="text-blue-600 hover:underline">Create your first event</a>
            </p>
          </div>
        }
      >
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
                <TableRow class='hover:bg-blend-color-burn'
                  on:click={() => navigate({ to: '/events/$eventId', params: { eventId: event.slug } })}>
                  <TableCell>{event.name}</TableCell>
                  <TableCell>{event.startDate}</TableCell>
                  <TableCell>{event.endDate}</TableCell>
                  <TableCell>{event.seats}</TableCell>
                </TableRow>
              )}
            </For>
          </TableBody>
        </Table>
      </Show>
    </Suspense>
  )
};

function RouteComponent() {
  return (
    <>
      <Tabs.Root defaultValue="current" class="w-full align-middle mx-auto max-w-fit pt-5 px-10">
        <Tabs.List class='my-5 space-x-5 flex data-[orientation=vertical]:flex-col allign-middle'>
          <Tabs.Trigger class='relative' value={EventTimeWhen.CURRENT}>Current Events</Tabs.Trigger>
          <Tabs.Trigger class='relative' value={EventTimeWhen.UPCOMING}>Upcoming Events</Tabs.Trigger>
          <Tabs.Trigger class='relative' value={EventTimeWhen.PAST}>Past Events</Tabs.Trigger>
          <Tabs.Indicator class='h-4px bg-red-600 z-10' />
        </Tabs.List>
        <div class="w-full border-b-2 border-b-white" />
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
    </>
  );
}
