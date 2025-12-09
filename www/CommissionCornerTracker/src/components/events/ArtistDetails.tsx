import { useQuery } from '@tanstack/solid-query';
import { Suspense, Show } from 'solid-js';
import { Dialog, Timer } from '@ark-ui/solid';
import { fetchArtist } from '../../api/artists';
import unknown_pfp from "../../../assets/unknown_pfp.png";

export function ArtistDetails(params: { artistId: string }) {
  const artistData = useQuery(() => ({
    queryKey: [params.artistId],
    queryFn: () => fetchArtist(params.artistId),
    refetchInterval: 1000 * 60,
    refetchIntervalInBackground: true,
    refetchOnMount: true
  }));

  return (
    <Suspense fallback={<div class="flex items-center justify-center p-8 text-gray-500 dark:text-gray-400">Loading Artist Details...</div>}>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 flex-1">
        <div class="flex items-center space-x-4 mb-6">
          <Dialog.Root>
            <Dialog.Trigger>
              <img
                class={`w-16 h-16 rounded-full object-cover border-4 cursor-pointer hover:opacity-80 transition-opacity ${artistData.data?.active ? 'artist-avatar-active' : 'artist-avatar-inactive'}`}
                src={unknown_pfp}
                alt={artistData.data?.name}
              />
            </Dialog.Trigger>
            <Dialog.Backdrop class="fixed inset-0 bg-black/50 z-40" />
            <Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
              <Dialog.Content class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-lg max-h-[50vh] w-full">
                <div class="text-center space-y-4">
                  <h3 class="text-xl font-semibold text-gray-800 dark:text-gray-200">
                    {artistData.data?.name}
                  </h3>
                  <img
                    class="mx-auto max-w-full max-h-[40vh] object-contain rounded-lg"
                    src={unknown_pfp}
                    alt={artistData.data?.name}
                  />
                  <a
                    href={artistData.data?.profileUrl}
                    class="inline-block text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Check them out!
                  </a>
                </div>
                <Dialog.CloseTrigger class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                  ✕
                </Dialog.CloseTrigger>
              </Dialog.Content>
            </Dialog.Positioner>
          </Dialog.Root>

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
        </div>

        <div class="pt-5 border-t border-gray-200 dark:border-gray-600">
          <div class='flex flex-row gap-3'>
            <div class="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 px-3 py-2 rounded-lg text-sm font-medium text-center flex-1">
              Taking Commissions!
            </div>
            {artistData.data?.commissionsRemaining !== null && (
              <div class="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 px-3 py-2 rounded-lg text-sm font-medium text-center flex-1">
                {artistData.data?.commissionsRemaining} spots left!
              </div>
            )}
          </div>
        </div>

        <div class='pt-4'>
          <Show when={artistData.data?.timeRemaining !== null && artistData.data!.timeRemaining > 0}>
            <div class="text-center">
              <h4 class="text-sm font-normal text-gray-600 dark:text-gray-400 mb-2">Time Remaining</h4>
              <Timer.Root autoStart countdown startMs={artistData.data!.timeRemaining! * 1000}>
                <Timer.Area class="flex items-center justify-center space-x-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-3">
                  <Timer.Item type='hours' class="text-2xl font-mono font-bold text-gray-800 dark:text-gray-200 min-w-[2ch] text-center" />
                  <Timer.Separator class="text-xl font-bold text-gray-600 dark:text-gray-400">:</Timer.Separator>
                  <Timer.Item type='minutes' class="text-2xl font-mono font-bold text-gray-800 dark:text-gray-200 min-w-[2ch] text-center" />
                  <Timer.Separator class="text-xl font-bold text-gray-600 dark:text-gray-400">:</Timer.Separator>
                  <Timer.Item type='seconds' class="text-2xl font-mono font-bold text-gray-800 dark:text-gray-200 min-w-[2ch] text-center" />
                </Timer.Area>
              </Timer.Root>
            </div>
          </Show>
        </div>
      </div>
    </Suspense>
  )
}