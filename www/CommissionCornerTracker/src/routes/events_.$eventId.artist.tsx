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
    <div class='flex flex-col gap-4'>
      <Editable.Root placeholder={artistDetails.name}
        onValueCommit={(value: EditableValueChangeDetails) => setArtistDetails("name", value.value)}>
        <Editable.Label>Artist Name</Editable.Label>
        <Editable.Area>
          <Editable.Input />
          <Editable.Preview />
        </Editable.Area>
      </Editable.Root>
      <div>Profile Picture</div>
      <FileUpload.Root accept={['image/*']}>
        <FileUpload.Label>Upload Profile Picture</FileUpload.Label>
        <FileUpload.Trigger>Choose An Image</FileUpload.Trigger>
        <FileUpload.ItemGroup>
          <FileUpload.Context>
            {(context) => (
              <For each={context().acceptedFiles}>
                {(file) => (
                  <FileUpload.Item file={file}>
                    <FileUpload.ItemPreviewImage />
                    <FileUpload.ItemDeleteTrigger>X</FileUpload.ItemDeleteTrigger>
                  </FileUpload.Item>
                )}
              </For>
            )}
          </FileUpload.Context>
        </FileUpload.ItemGroup>
        <FileUpload.HiddenInput />
      </FileUpload.Root>
      <Editable.Root placeholder={artistDetails.details}
        onValueCommit={(value: EditableValueChangeDetails) => setArtistDetails("details", value.value)}>
        <Editable.Label>Details</Editable.Label>
        <Editable.Area>
          <Editable.Input />
          <Editable.Preview />
        </Editable.Area>
      </Editable.Root>
      <Editable.Root placeholder="Social Media or Shop URL">
        <Editable.Label>Social Media or Shop URL</Editable.Label>
        <Editable.Area>
          <Editable.Input />
          <Editable.Preview />
        </Editable.Area>
      </Editable.Root>
      <ToggleGroup.Root defaultValue={[CommissionStatus.OPEN]} deselectable={false}
        onValueChange={(context: ToggleGroupValueChangeDetails) => updateCommissionStatus(context.value as CommissionStatus[])}>
        <ToggleGroup.Item value={CommissionStatus.CLOSED}>Closed</ToggleGroup.Item>
        <ToggleGroup.Item value={CommissionStatus.OPEN}>Open</ToggleGroup.Item>
        <ToggleGroup.Item value={CommissionStatus.COUNT}>Open with Limit</ToggleGroup.Item>
      </ToggleGroup.Root>
      <Switch>
        <Match when={commissionStatus() === CommissionStatus.OPEN}>
          <div class="text-center">
            <h4 class="text-sm font-normal text-gray-600 dark:text-gray-400 mb-2">Commissions Open with no limits.</h4>
          </div>
        </Match>
        <Match when={commissionStatus() === CommissionStatus.COUNT}>
          <NumberInput.Root>
            <NumberInput.Label>Commission Count</NumberInput.Label>
            <NumberInput.Control>
              <NumberInput.Input />
              <NumberInput.IncrementTrigger>+</NumberInput.IncrementTrigger>
              <NumberInput.DecrementTrigger>-</NumberInput.DecrementTrigger>
            </NumberInput.Control>
          </NumberInput.Root>
        </Match>
      </Switch>
      <DoubleClickButton onConfirm={() => console.log("Relinquish Seat Placeholder")}
        initialText="Relinquish Seat"
        initialClass="bg-gray-200 text-black"
        confirmText="Are you sure? (Click again to confirm)"
        confirmClass="bg-red-600 text-white"
      />

      <div class="absolute bottom-16">
        {JSON.stringify(artistDetails)}
      </div>
    </div>
  )
}
