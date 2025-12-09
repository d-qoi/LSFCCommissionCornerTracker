import { useQuery } from '@tanstack/solid-query';
import { createMemo, For, Suspense } from 'solid-js';
import { fetchEvent, fetchEventArtists } from '../../api/events';
import { ArtistSummary } from '../../api/artists';
import { ArtistSeat } from './ArtistSeat';

interface EventSeatsProps {
  eventId: string;
  onArtistSelect: (artistSlug: string | null) => void;
}

export function EventSeats(props: EventSeatsProps) {
  const eventData = useQuery(() => ({
    queryKey: [props.eventId],
    queryFn: () => fetchEvent(props.eventId),
    refetchInterval: 1000 * 60,
    refetchIntervalInBackground: true,
  }));

  const eventArtistSummary = useQuery(() => ({
    queryKey: [props.eventId, 'artist summary'],
    queryFn: () => fetchEventArtists(props.eventId),
    refetchInterval: 1000 * 60,
    refetchIntervalInBackground: true,
  }));

  const artistSeats = createMemo(() => {
    if (!eventData.data || !eventArtistSummary.data) {
      return null;
    }
    const seats = new Array(eventData.data.seats).fill(null);
    eventArtistSummary.data.forEach((artist: ArtistSummary) => {
      seats[artist.seat - 1] = artist;
    });
    return seats;
  });

  return (
    <Suspense fallback={<div class="text-gray-500 dark:text-gray-400">Loading seats...</div>}>
      <div class="flex flex-col w-1/3 bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="flex flex-row justify-between mb-4 text-sm font-medium text-gray-600 dark:text-gray-400">
          <div>Total Seats: <span class="text-gray-800 dark:text-gray-200">{eventData.data?.seats}</span></div>
          <div>Available: <span class="text-green-600 dark:text-green-400">{eventData.data?.seatsAvailable}</span></div>
        </div>

        <div class="space-y-2">
          <For each={artistSeats()}>
            {(artist: ArtistSummary | null, index) => (
              <ArtistSeat
                artist={artist}
                index={index()}
                onSelect={props.onArtistSelect}
              />
            )}
          </For>
        </div>
      </div>
    </Suspense>
  );
}