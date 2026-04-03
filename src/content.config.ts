import { defineCollection, z } from 'astro:content';
import { file, glob } from 'astro/loaders';

const site = defineCollection({
  loader: file('src/content/site/site.json'),
  schema: z.object({
    title: z.string(),
    subtitle: z.string(),
    description: z.string(),
    conferenceName: z.string(),
    conferenceDescription: z.string(),
    conferenceUrl: z.string().url(),
    workshopDate: z.string(),
    location: z.string(),
    contactEmail: z.string().email(),
    openReviewUrl: z.string(),
    submissionTemplateUrl: z.string(),
    showAcceptedPapers: z.boolean(),
    showSpeakers: z.boolean(),
    showProgram: z.boolean(),
    deadlines: z.array(
      z.object({
        item: z.string(),
        date: z.string(),
      }),
    ),
    previousWorkshops: z.array(
      z.object({
        title: z.string(),
        url: z.string().url(),
      }),
    ),
  }),
});

const navigation = defineCollection({
  loader: file('src/content/navigation/menu.json'),
  schema: z.object({
    items: z.array(
      z.object({
        title: z.string(),
        url: z.string(),
        key: z.string().optional(),
      }),
    ),
  }),
});

const pages = defineCollection({
  loader: glob({ base: './src/content/pages', pattern: '**/*.md' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
  }),
});

const speakers = defineCollection({
  loader: file('src/content/speakers/speakers.json'),
  schema: z.object({
    id: z.string(),
    name: z.string(),
    affiliation: z.string(),
    website: z.string().nullable(),
    image: z.string().nullable(),
    note: z.string(),
    tentative: z.boolean(),
  }),
});

const organizers = defineCollection({
  loader: file('src/content/organizers/organizers.json'),
  schema: z.object({
    id: z.string(),
    name: z.string(),
    affiliation: z.string(),
    website: z.string().url(),
    image: z.string().nullable(),
  }),
});

const papers = defineCollection({
  loader: file('src/content/papers/papers.json'),
  schema: z.object({
    id: z.string(),
    title: z.string(),
    authors: z.string(),
    status: z.string(),
    pdfUrl: z.string().nullable(),
    videoUrl: z.string().nullable(),
    session: z.string().nullable(),
    placeholder: z.boolean(),
  }),
});

const schedule = defineCollection({
  loader: file('src/content/schedule/workshop.json'),
  schema: z.object({
    time: z.string(),
    session: z.string(),
  }),
});

export const collections = {
  site,
  navigation,
  pages,
  speakers,
  organizers,
  papers,
  schedule,
};
