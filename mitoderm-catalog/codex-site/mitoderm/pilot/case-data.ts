export interface VTechCase {
  id: string;
  title: string;
  before: {src: string; alt: string};
  after: {src: string; alt: string};
  assessment: string;
  sessions: string;
  program: string;
  details?: string;
  product: 'v-tech-system';
  publicationApproved: boolean;
  sourceVerified: boolean;
}
// Only product-attributed, publication-approved cases may be added here.
// The provided archive does not contain an approved V-Tech before/after pair.
export const vtechCases: readonly VTechCase[] = [];
