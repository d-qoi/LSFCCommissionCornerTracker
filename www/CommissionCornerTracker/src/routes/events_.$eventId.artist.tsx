import { createFileRoute, useParams } from '@tanstack/solid-router'
import { Editable, EditableValueChangeDetails, FileUpload, NumberInput, ToggleGroup, ToggleGroupValueChangeDetails } from '@ark-ui/solid'
import { createSignal, For, Match, Show, Switch } from 'solid-js'
import { createStore } from 'solid-js/store'
import { makePersisted } from '@solid-primitives/storage'
import { Artist, ArtistCustomizableDetails } from '@/api/artists';
import { DoubleClickButton } from '@/components/DoubleClickButton'

export const Route = createFileRoute('/events_/$eventId/artist')({
  component: RouteComponent,
})

enum CommissionStatus {
  OPEN = 'open',
  CLOSED = 'closed',
  COUNT = 'count',
}

function RouteComponent() {
  const params = useParams({ strict: false });
  const [commissionStatus, setCommissionStatus] = createSignal<CommissionStatus>(CommissionStatus.OPEN);

  const [artistDetails, setArtistDetails] = makePersisted(
    createStore<ArtistCustomizableDetails>(
      {
        name: "Test",
        details: "Details",
        imageUrl: "example.com",
        profileUrl: "example.com",
        commissionsOpen: true,
        commissionsRemaining: 5,
      }
    ),
    {
      name: `artistDetails`,
    }
  );



  const updateCommissionStatus = (value: CommissionStatus[]) => {
    console.log("Update Commission Status", value[0]);
    setCommissionStatus(value[0]);
  }

  return (
    <div class="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-8 w-full max-w-md">
      <div class="flex items-center space-x-4 mb-6">
        <div>
          <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Profile Picture</h4>
          <FileUpload.Root accept={['image/*']}>
            <FileUpload.Trigger class="w-16 h-16 rounded-full border-4 border-dashed border-gray-300 dark:border-gray-600 flex items-center justify-center text-xs hover:border-gray-400 transition-colors">
              +
            </FileUpload.Trigger>
            <FileUpload.ItemGroup>
              <FileUpload.Context>
                {(context) => (
                  <For each={context().acceptedFiles}>
                    {(file) => (
                      <FileUpload.Item file={file} class="relative">
                        <FileUpload.ItemPreviewImage class="w-16 h-16 rounded-full object-cover border-4 border-gray-300 dark:border-gray-600" />
                        <FileUpload.ItemDeleteTrigger class="absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-xs bg-inactive">
                          ✕
                        </FileUpload.ItemDeleteTrigger>
                      </FileUpload.Item>
                    )}
                  </For>
                )}
              </FileUpload.Context>
            </FileUpload.ItemGroup>
            <FileUpload.HiddenInput />
          </FileUpload.Root>
        </div>

        <div class="flex-1">
          <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Artist Name</h4>
          <Editable.Root placeholder={artistDetails.name}
            onValueCommit={(value: EditableValueChangeDetails) => setArtistDetails("name", value.value)}>
            <Editable.Area>
              <Editable.Input class="text-xl font-semibold px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200" />
              <Editable.Preview class="text-xl font-semibold text-gray-800 dark:text-gray-200" />
            </Editable.Area>
          </Editable.Root>
        </div>
      </div>

      <div class="space-y-4">

        <div>
          <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Details</h4>
          <Editable.Root placeholder={artistDetails.details}
            onValueCommit={(value: EditableValueChangeDetails) => setArtistDetails("details", value.value)}>
            <Editable.Area>
              <Editable.Input class="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200" />
              <Editable.Preview class="text-gray-800 dark:text-gray-200" />
            </Editable.Area>
          </Editable.Root>
        </div>

        <div>
          <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Profile</h4>
          <Editable.Root placeholder="Social Media or Shop URL">
            <Editable.Area>
              <Editable.Input class="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200" />
              <Editable.Preview class="underline break-all text-accent" />
            </Editable.Area>
          </Editable.Root>
        </div>
      </div>

      <div class="pt-5 border-t border-gray-200 dark:border-gray-600">
        <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">Commission Status</h4>
        <ToggleGroup.Root defaultValue={[CommissionStatus.OPEN]} deselectable={false}
          onValueChange={(context: ToggleGroupValueChangeDetails) => updateCommissionStatus(context.value as CommissionStatus[])}>
          <div class="flex gap-2">
            <ToggleGroup.Item value={CommissionStatus.CLOSED}>
              Closed
            </ToggleGroup.Item>
            <ToggleGroup.Item value={CommissionStatus.OPEN}>
              Open
            </ToggleGroup.Item>
            <ToggleGroup.Item value={CommissionStatus.COUNT}>
              Open with Limit
            </ToggleGroup.Item>
          </div>
        </ToggleGroup.Root>

        <div class="mt-4">
          <Switch>
            <Match when={commissionStatus() === CommissionStatus.OPEN}>
              <div class="px-3 py-2 rounded-lg text-sm font-medium text-center bg-active">
                Commissions Open with no limits
              </div>
            </Match>
            <Match when={commissionStatus() === CommissionStatus.COUNT}>
              <NumberInput.Root>
                <NumberInput.Label class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2 block">Commission Count</NumberInput.Label>
                <NumberInput.Control class="flex">
                  <NumberInput.Input class="flex-1 px-3 py-2 border rounded-l-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200" />
                  <NumberInput.IncrementTrigger class="px-3 py-2 border border-l-0">+</NumberInput.IncrementTrigger>
                  <NumberInput.DecrementTrigger class="px-3 py-2 border border-l-0 rounded-r-lg">-</NumberInput.DecrementTrigger>
                </NumberInput.Control>
              </NumberInput.Root>
            </Match>
          </Switch>
        </div>
      </div>

      <div class="pt-5 border-t border-gray-200 dark:border-gray-600">
        <DoubleClickButton onConfirm={() => console.log("Relinquish Seat Placeholder")}
          initialText="Relinquish Seat"
          initialClass="w-full px-4 py-2 rounded-lg transition-colors"
          confirmText="Are you sure? (Click again to confirm)"
          confirmClass="w-full px-4 py-2 rounded-lg transition-colors"
        />
      </div>

        <div class="mt-6 pt-4 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-500 dark:text-gray-400">
          {JSON.stringify(artistDetails)}
        </div>
      </div>
    </div>
  )
}
