import { useQuery } from '@tanstack/solid-query';
import { createFileRoute, useParams } from '@tanstack/solid-router'
import { fetchAllEvents, EventDetails } from '@/api/events';
import { createMemo, createSignal, Match, Show, Suspense, Switch } from 'solid-js';
import { ArtistDetails } from '@/components/events/ArtistDetails';
import { EventSeats } from '@/components/events/EventSeats';

export const Route = createFileRoute('/events_/$eventId/')({
  validateSearch: (search: Record<string, unknown>) => ({
    artist: (search.artist as string),
  }),
  component: () => (
    <Suspense fallback={<div>Loading page...</div>}>
      <CurrentEventComponent />
    </Suspense>
  ),
})


function CurrentEvent(params: { eventId: string }) {
  const search = Route.useSearch();
  const nav = Route.useNavigate();
  const [selectedArtist, setSelectedArtist] = createSignal<string | null>(search().artist || null);

  const updateSelectedArtist = (artist: string | null) => {
    if (!artist) {
      nav({
        search: {artist: ""},
        replace: true
      })
    } else {
      nav({
        search: {
          artist: artist,
        },
        replace: true,
      })
    }
    setSelectedArtist(artist);
  }

  return (
    <div class="flex flex-row w-full gap-6">
      <EventSeats eventId={params.eventId} onArtistSelect={updateSelectedArtist} />

      <Show when={selectedArtist()}>
        <ArtistDetails artistId={selectedArtist()!} />
      </Show>
      <Show when={!selectedArtist()}>
        <div class="flex items-center justify-center p-8 text-gray-500 dark:text-gray-400">Select an artist to view details</div>
      </Show>
    </div>
  )
}

function CurrentEventComponent() {
  const params = useParams({ strict: false });

  const allEvents = useQuery(() => ({
    queryKey: ['events'],
    queryFn: fetchAllEvents,
    refetchOnMount: true,
  }));

  const eventData = createMemo(() => {
    if (!allEvents.data) {
      return null;
    }

    for (const [key, value] of Object.entries(allEvents.data)) {
      const event = value.find((event: EventDetails) => event.slug === params().eventId);
      if (event) {
        return { event: event, key: key };
      }
    }

    return null;
  });

  return (
    <div class="max-w-7xl mx-auto px-4 py-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-800 dark:text-gray-200 mb-2">
          {eventData()?.event.name}
        </h1>
        <p class="text-gray-600 dark:text-gray-400">
          Hosted by{' '}
          <a
            href={eventData()?.event.hostedByUrl}
            class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {eventData()?.event.hostedBy}
          </a>
        </p>
      </div>

      <Switch>
        <Match when={eventData()?.key === 'current'}>
          <div class="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <p class="text-green-800 dark:text-green-200">
              This event is currently running until {eventData()?.event.endDate}
            </p>
          </div>
          <CurrentEvent eventId={params().eventId!} />
        </Match>
        <Match when={eventData()?.key === 'upcoming'}>
          <div class="p-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-center">
            <h3 class="text-lg font-medium text-blue-800 dark:text-blue-200 mb-2">Event Not Started</h3>
            <p class="text-blue-600 dark:text-blue-300">
              This event has not started yet. Please check back on {eventData()?.event.startDate}
            </p>
          </div>
        </Match>
        <Match when={eventData()?.key === 'past'}>
          <div class="p-8 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-center">
            <h3 class="text-lg font-medium text-gray-800 dark:text-gray-200 mb-2">Event Ended</h3>
            <p class="text-gray-600 dark:text-gray-400">This event has ended.</p>
          </div>
        </Match>
      </Switch>
    </div>
  )
}
