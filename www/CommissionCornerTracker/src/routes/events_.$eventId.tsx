import { useQuery } from '@tanstack/solid-query';
import { createFileRoute, useNavigate, useParams, useSearch } from '@tanstack/solid-router'
import { fetchAllEvents, EventDetails, EventTimeWhen, fetchEvent, fetchEventArtists } from '../api/events';
import { createMemo, createSignal, For, Match, Show, Suspense, Switch } from 'solid-js';
import { Artist, ArtistSummary, fetchArtist } from '../api/artists';
import { Table, TableBody, TableCell, TableRow } from '../components/table';
import { Avatar } from '@ark-ui/solid';
import unknown_pfp from "../../assets/unknown_pfp.png";

export const Route = createFileRoute('/events_/$eventId')({
  validateSearch: (search: Record<string, unknown>) => ({
    artist: (search.artist as string) || undefined,
  }),
  component: () => (
    <Suspense fallback={<div>Loading page...</div>}>
      <CurrentEventComponent />
    </Suspense>
  ),
})

function ArtistDetails(params: { artistId: string }) {
  const artistData = useQuery(() => ({
    queryKey: [params.artistId],
    queryFn: () => fetchArtist(params.artistId),
    refetchInterval: 1000 * 60, // refresh every minute
    refetchIntervalInBackground: true,
    refetchOnMount: true
  }))

  return (
    <Suspense fallback={<div class="flex items-center justify-center p-8 text-gray-500 dark:text-gray-400">Loading Artist Details...</div>}>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-md">
        <div class="flex items-center space-x-4 mb-6">
          <img
            class={`w-16 h-16 rounded-full object-cover border-4 ${artistData.data?.active ? 'artist-avatar-active' : 'artist-avatar-inactive'
              }`}
            src={unknown_pfp}
            alt={artistData.data?.name}
          />
          <div>
            <h3 class="text-xl font-semibold text-gray-800 dark:text-gray-200">{artistData.data?.name}</h3>
            <div class={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${artistData.data?.active
              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
              }`}>
              {artistData.data?.active ? 'Active' : 'Inactive'}
            </div>
          </div>
        </div>

        <div class="space-y-4">
          <div>
            <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Details</h4>
            <p class="text-gray-800 dark:text-gray-200">{artistData.data?.details || 'No details available'}</p>
          </div>

          <div>
            <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Profile</h4>
            <a
              href={artistData.data?.profileUrl}
              class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline break-all"
              target="_blank"
              rel="noopener noreferrer"
            >
              {artistData.data?.profileUrl}
            </a>
          </div>

          <div class="pt-2 border-t border-gray-200 dark:border-gray-600">
            {artistData.data?.commissionsRemaining !== null ? (
              <div class="flex items-center space-x-2">
                <span class="text-sm font-medium text-gray-600 dark:text-gray-400">Commissions Remaining:</span>
                <span class="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 px-2 py-1 rounded-full text-sm font-medium">
                  {artistData.data?.commissionsRemaining}
                </span>
              </div>
            ) : (
              <div class="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 px-3 py-2 rounded-lg text-sm font-medium text-center">
                Taking Commissions!
              </div>
            )}
          </div>
        </div>
      </div>
    </Suspense>
  )
}

function CurrentEvent(params: { eventId: string }) {
  const search = Route.useSearch();
  const nav = Route.useNavigate();
  const [selectedArtist, setSelectedArtist] = createSignal<string | null>(search().artist || null);
  const eventData = useQuery(() => ({
    queryKey: [params.eventId],
    queryFn: () => fetchEvent(params.eventId),
    refetchInterval: 1000 * 60, // refresh every minute
    refetchIntervalInBackground: true,
  }))

  const eventArtistSummary = useQuery(() => ({
    queryKey: [params.eventId, 'artist summary'],
    queryFn: () => fetchEventArtists(params.eventId),
    refetchInterval: 1000 * 60, // refresh every minute
    refetchIntervalInBackground: true,
  }));

  const artistSeats = createMemo(() => {
    if (!eventData.data || !eventArtistSummary.data) {
      return null;
    }
    const seats = new Array(eventData.data.seats).fill(null);
    eventArtistSummary.data.forEach((artist: ArtistSummary) => {
      seats[artist.seat - 1] = artist;
    })

    return seats;
  })

  const updateSelectedArtist = (artist: string | null) => {
    if (!artist) {
      nav({
        search: { artist: undefined },
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
      <Suspense fallback={<div class="text-gray-500 dark:text-gray-400">Loading seats...</div>}>
        <div class="flex flex-col w-1/3 bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div class="flex flex-row justify-between mb-4 text-sm font-medium text-gray-600 dark:text-gray-400">
            <div>Total Seats: <span class="text-gray-800 dark:text-gray-200">{eventData.data?.seats}</span></div>
            <div>Available: <span class="text-green-600 dark:text-green-400">{eventData.data?.seatsAvailable}</span></div>
          </div>

          <div class="space-y-2">
            <For each={artistSeats()}>
              {(artist: ArtistSummary | null, index) => (
                <div
                  class="seat-item flex items-center space-x-3 p-2 rounded-md cursor-pointer transition-colors"
                  onClick={() => updateSelectedArtist(artist?.slug || null)}
                >
                  <Switch>
                    <Match when={artist !== null}>
                      <span class="text-sm font-medium text-gray-600 dark:text-gray-400 w-6">{artist.seat}:</span>
                      <Avatar.Root class="w-8 h-8">
                        <Avatar.Image src={unknown_pfp} />
                        <Avatar.Fallback class="bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs">
                          {artist.name.charAt(0)}
                        </Avatar.Fallback>
                      </Avatar.Root>
                      <span class="text-gray-800 dark:text-gray-200 text-sm">{artist.name}</span>
                    </Match>
                    <Match when={!artist}>
                      <span class="text-sm text-gray-500 dark:text-gray-500 w-6">{index() + 1}:</span>
                      <div class="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 border-2 border-dashed border-gray-300 dark:border-gray-600"></div>
                      <span class="text-gray-400 dark:text-gray-500 text-sm italic">Empty seat</span>
                    </Match>
                  </Switch>
                </div>
              )}
            </For>
          </div>
        </div>
      </Suspense>

      <Show when={selectedArtist()}>
        <ArtistDetails artistId={selectedArtist()!} />
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
    <>
      <div><h1>{eventData()?.event.name}</h1></div>
      <div>Hosted By <a href={eventData()?.event.hostedByUrl}>{eventData()?.event.hostedBy}</a></div>
      <Switch>
        <Match when={eventData()?.key === 'current'}>
          <div>This event is running till {eventData()?.event.endDate}</div>
          <CurrentEvent eventId={params().eventId} />
        </Match>
        <Match when={eventData()?.key === 'upcoming'}>
          <div>This event has not started yet. Please check back on {eventData()?.event.startDate}</div>
        </Match>
        <Match when={eventData()?.key === 'past'}>
          <div>This event has ended.</div>
        </Match>
      </Switch>
    </>
  )
}
