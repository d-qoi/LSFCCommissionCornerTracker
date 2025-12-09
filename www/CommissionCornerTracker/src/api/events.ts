import { Artist, ArtistSummary, MockArtistData } from "./artists";

export interface EventDetails {
  name: string;
  slug: string;
  hostedBy: string;
  hostedByUrl: string;
  startDate: string;
  endDate: string;
  seats: number;
  seatsAvailable: number | null;
}

export interface EventsData {
  current: EventDetails[];
  upcoming: EventDetails[];
  past: EventDetails[];
}

export enum EventTimeWhen {
  CURRENT = "current",
  UPCOMING = "upcoming",
  PAST = "past",
}

const MockEventData: EventsData = {
  current: [
    {
      name: "Event 1",
      slug: "event-1",
      hostedBy: "LSFC",
      hostedByUrl: "http://lonestarfurcon.com/",
      startDate: "2025-12-01",
      endDate: "2025-12-02",
      seats: 10,
      seatsAvailable: 5,
    },
    {
      name: "Event 2",
      slug: "event-2",
      hostedBy: "LSFC",
      hostedByUrl: "http://lonestarfurcon.com/",
      startDate: "2025-12-01",
      endDate: "2025-12-02",
      seats: 11,
      seatsAvailable: 4,
    },
    {
      name: "Event 3",
      slug: "event-3",
      hostedBy: "LSFC",
      hostedByUrl: "http://lonestarfurcon.com/",
      startDate: "2025-12-01",
      endDate: "2025-12-02",
      seats: 4,
      seatsAvailable: 4,
    },
  ],
  upcoming: [
    {
      name: "Event 4",
      slug: "event-4",
      hostedBy: "LSFC",
      hostedByUrl: "http://lonestarfurcon.com/",
      startDate: "2025-12-10",
      endDate: "2025-12-12",
      seats: 1,
      seatsAvailable: 0,
    },
    {
      name: "Event 5",
      slug: "event-5",
      hostedBy: "LSFC",
      hostedByUrl: "http://lonestarfurcon.com/",
      startDate: "2025-12-11",
      endDate: "2025-12-12",
      seats: 12,
      seatsAvailable: 0,
    },
    {
      name: "Event 6",
      slug: "event-6",
      hostedBy: "LSFC",
      hostedByUrl: "http://lonestarfurcon.com/",
      startDate: "2025-12-12",
      endDate: "2025-12-12",
      seats: 3,
      seatsAvailable: 0,
    },
  ],
  past: [],
};

export const fetchAllEvents = async (): Promise<EventsData> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(MockEventData);
    }, 5000);
  });
};

export const fetchEvent = async (eventId: string): Promise<EventDetails> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      for (const [key, value] of Object.entries(MockEventData)) {
        const event = value.find(
          (event: EventDetails) => event.slug === eventId
        );
        if (event) {
          resolve(event);
        }
      }
      throw new Error("Event Not Found");
    }, 5000);
  });
};

export const fetchEventArtists = async (
  eventId: string
): Promise<ArtistSummary[]> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      const artists = MockArtistData.filter(
        (artist) => artist.eventId === eventId
      );
      const artistSummaries = artists.map(
        (artist, index): ArtistSummary => ({
          name: artist.name,
          slug: artist.slug,
          eventId: artist.eventId,
          imageUrl: artist.imageUrl,
          seat: index + 2,
        })
      );
      resolve(artistSummaries);
    }, 100);
  });
};
