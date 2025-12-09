import { createFileRoute } from '@tanstack/solid-router';

export const Route = createFileRoute('/')({
  component: Home,
});

function Home() {
  return (
    <div class="max-w-4xl mx-auto px-4 py-8">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
        <h1 class="text-3xl font-bold text-gray-800 dark:text-gray-200 mb-6">
          Welcome to the LSFC Commission Corner Tracker!
        </h1>

        <div class="space-y-6">
          <section>
            <h2 class="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-4">
              How these events work:
            </h2>

            <div class="space-y-4 text-gray-600 dark:text-gray-400 leading-relaxed">
              <p>
                Each event lists a number of seats. These seats can be filled by any artist that is taking commissions.
              </p>

              <p>
                Artists need to approach the event runner to claim a seat. They will be given a QR Code to scan with their phone.
              </p>

              <p>
                This will let them create a temporary profile for the event, which will be shown to anyone who visits the site!
              </p>
            </div>
          </section>

          <section class="pt-6 border-t border-gray-200 dark:border-gray-600">
            <div class="space-y-4 text-gray-600 dark:text-gray-400 leading-relaxed">
              <p>
                If you want to host an event, please create an account and request permissions on your profile!
                We will enable it and send you an email within the hour.
              </p>

              <p>
                If an artist wants to use the same information for multiple events, they can create a profile
                and save their information there.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
