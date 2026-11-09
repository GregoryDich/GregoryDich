export interface StorySection {
  index: number;
  eyebrow?: string;
  title: string;
  body: string;
  tags: string;
  cta: string;
}
export interface Product {
  slug: string;
  name: string;
  line: string;
  intro: StorySection;
  sections: StorySection[];
  source_note?: string;
}
export interface ProductAsset {
  src: string;
  width: number;
  height: number;
  maxWidth: number;
  source: string;
}
