import { Match, Switch } from 'solid-js';
import { Avatar } from '@ark-ui/solid';
import { ArtistSummary } from '../../api/artists';
import unknown_pfp from "../../../assets/unknown_pfp.png";

interface ArtistSeatProps {
  artist: ArtistSummary | null;
  index: number;
  onSelect: (artistSlug: string | null) => void;
}

export function ArtistSeat(props: ArtistSeatProps) {
  return (
    <div
      class="seat-item flex items-center space-x-3 p-2 rounded-md cursor-pointer transition-colors"
      onClick={() => props.onSelect(props.artist?.slug || null)}
    >
      <Switch>
        <Match when={props.artist !== null}>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400 w-6">{props.artist!.seat}:</span>
          <Avatar.Root class="w-8 h-8">
            <Avatar.Image src={unknown_pfp} />
            <Avatar.Fallback class="bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs">
              {props.artist!.name.charAt(0)}
            </Avatar.Fallback>
          </Avatar.Root>
          <span class="text-gray-800 dark:text-gray-200 text-sm">{props.artist!.name}</span>
        </Match>
        <Match when={!props.artist}>
          <span class="text-sm text-gray-500 dark:text-gray-500 w-6">{props.index + 1}:</span>
          <div class="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 border-2 border-dashed border-gray-300 dark:border-gray-600"></div>
          <span class="text-gray-400 dark:text-gray-500 text-sm italic">Empty seat</span>
        </Match>
      </Switch>
    </div>
  );
}