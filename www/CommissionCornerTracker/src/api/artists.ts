export interface Artist {
  name: string;
  slug: string;
  eventId: string;
  details: string;
  imageUrl: string;
  profileUrl: string;
  commissionsOpen: boolean;
  commissionsRemaining: number | null;
  active: boolean | null;
}

export interface ArtistSummary {
  name: string;
  slug: string;
  eventId: string;
  imageUrl: string;
  seat: number;
}

export const MockArtistData: Artist[] = [
  // Event 1 Artists
  {
    name: "Luna Starweaver",
    slug: "luna-starweaver",
    eventId: "event-1",
    details:
      "Digital artist specializing in fantasy creatures and celestial themes",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://twitter.com/lunastarweaver",
    commissionsOpen: true,
    commissionsRemaining: 3,
    active: true,
  },
  {
    name: "Crimson Paws",
    slug: "crimson-paws",
    eventId: "event-1",
    details: "Traditional artist focusing on anthropomorphic characters",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://furaffinity.net/user/crimsonpaws",
    commissionsOpen: true,
    commissionsRemaining: null,
    active: true,
  },
  {
    name: "Crimson 2",
    slug: "crimson-2",
    eventId: "event-1",
    details: "Traditional artist focusing on anthropomorphic characters",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://furaffinity.net/user/crimsonpaws",
    commissionsOpen: true,
    commissionsRemaining: null,
    active: false,
  },

  // Event 2 Artists
  {
    name: "Neon Tail Studios",
    slug: "neon-tail-studios",
    eventId: "event-2",
    details: "Cyberpunk and sci-fi themed furry art with vibrant colors",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://instagram.com/neontailstudios",
    commissionsOpen: false,
    commissionsRemaining: 0,
    active: true,
  },
  {
    name: "Whisker Dreams",
    slug: "whisker-dreams",
    eventId: "event-2",
    details: "Soft pastel artwork featuring cute and wholesome characters",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://deviantart.com/whiskerdreams",
    commissionsOpen: true,
    commissionsRemaining: 5,
    active: true,
  },
  {
    name: "Iron Claw Art",
    slug: "iron-claw-art",
    eventId: "event-2",
    details: "Bold, dynamic action scenes and character designs",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://artstation.com/ironclawart",
    commissionsOpen: true,
    commissionsRemaining: 2,
    active: true,
  },

  // Event 3 Artists
  {
    name: "Mystic Forest",
    slug: "mystic-forest",
    eventId: "event-3",
    details: "Nature-inspired artwork with magical forest creatures",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://twitter.com/mysticforestarts",
    commissionsOpen: true,
    commissionsRemaining: 1,
    active: true,
  },
  {
    name: "Pixel Pounce",
    slug: "pixel-pounce",
    eventId: "event-3",
    details: "Retro pixel art and 8-bit style character sprites",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://pixiv.net/users/pixelpounce",
    commissionsOpen: true,
    commissionsRemaining: null,
    active: true,
  },

  // Event 4 Artists
  {
    name: "Aurora Wings",
    slug: "aurora-wings",
    eventId: "event-4",
    details: "Ethereal winged creatures and celestial landscapes",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://furaffinity.net/user/aurorawings",
    commissionsOpen: false,
    commissionsRemaining: 0,
    active: true,
  },
  {
    name: "Sketch & Snout",
    slug: "sketch-and-snout",
    eventId: "event-4",
    details: "Quick sketches and character studies with expressive poses",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://twitter.com/sketchandsnout",
    commissionsOpen: true,
    commissionsRemaining: 4,
    active: true,
  },

  // Event 5 Artists
  {
    name: "Prism Fur Co",
    slug: "prism-fur-co",
    eventId: "event-5",
    details: "Colorful geometric patterns and abstract furry art",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://instagram.com/prismfurco",
    commissionsOpen: true,
    commissionsRemaining: 7,
    active: true,
  },
  {
    name: "Midnight Howl",
    slug: "midnight-howl",
    eventId: "event-5",
    details: "Dark fantasy and gothic-themed anthropomorphic characters",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://deviantart.com/midnighthowl",
    commissionsOpen: true,
    commissionsRemaining: 2,
    active: true,
  },
  {
    name: "Sunny Scales",
    slug: "sunny-scales",
    eventId: "event-5",
    details: "Bright, cheerful reptilian and dragon characters",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://furaffinity.net/user/sunnyscales",
    commissionsOpen: false,
    commissionsRemaining: 0,
    active: true,
  },

  // Event 6 Artists
  {
    name: "Velvet Brush",
    slug: "velvet-brush",
    eventId: "event-6",
    details: "Elegant portraits with rich textures and detailed fur rendering",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://artstation.com/velvetbrush",
    commissionsOpen: true,
    commissionsRemaining: 3,
    active: true,
  },
  {
    name: "Wild Strokes",
    slug: "wild-strokes",
    eventId: "event-6",
    details: "Expressive brushwork and dynamic wildlife-inspired characters",
    imageUrl: "https://placehold.co/200x200",
    profileUrl: "https://twitter.com/wildstrokes",
    commissionsOpen: true,
    commissionsRemaining: null,
    active: true,
  },
];

export async function fetchArtist(artistId: string): Promise<Artist> {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      const artist = MockArtistData.find((artist) => artist.slug === artistId);
      if (artist) {
        resolve(artist);
      } else {
        reject(new Error("Artist Not Found"));
      }
    }, 1000);
  });
}
