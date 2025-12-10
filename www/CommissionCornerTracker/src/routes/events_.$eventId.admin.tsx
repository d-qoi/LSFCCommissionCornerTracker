import { createFileRoute } from '@tanstack/solid-router'

export const Route = createFileRoute('/events_/$eventId/admin')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/events_/$eventId/admin"!</div>
}
