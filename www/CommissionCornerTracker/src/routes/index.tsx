import { createFileRoute } from '@tanstack/solid-router';

export const Route = createFileRoute('/')({
  component: Home,
});

function Home() {
  return (
    <div class="p-2">
      <h2>Welcome to the LSFC Commission Corner Tracker!</h2>
      <br />
      <h3>How these events work:</h3>
      <p>
        Each event lists a number of seats. These seats can be filled by any artist that is taking commissions.
        <br />
        Artists needs to approach the event runner to claim a seat. They will be given a QRCode to scan with their phone.
        <br />
        This will let them create a temprorary profile for the event, this profile will be shown on the event to anyone who visits the site!
        <br />
        <br />
        <br />
        If you want to host an event, please create an account and request permissions on your profile! We will get enable it and send you an email within the hour.
        <br />
        And if an artist wants to use the same information for multiple events, they can create a profile and save their information there.
      </p>
    </div>
  );
}
