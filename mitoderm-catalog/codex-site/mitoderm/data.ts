import contentJson from './content.json';
import assetsJson from './assets.json';
import type {Product, StorySection, ProductAsset} from './types';
export const content = contentJson;
export const products = contentJson.products as Product[];
export const home = contentJson.home as StorySection[];
export const ui = contentJson.ui as Record<string,string>;
export const formCopy = contentJson.form as Record<string,string>;
export const contact = contentJson.contact;
export const assets = assetsJson as Record<string, ProductAsset>;
export const lineKeys: Record<string,string> = {'V-TECH FACE':'vtech','PEELING':'peeling','BIOSPICULE':'biospicule','DEVICES':'devices','HAIR':'hair','MITOTECH':'mitotech'};
export const lineGroups = [
  {id:'vtech',name:'V-TECH FACE',section:2,products:['v-tech-system','exocell-mask','exotech-gel']},
  {id:'peeling',name:'PEELING',section:3,products:['exo-nad']},
  {id:'biospicule',name:'BIOSPICULE',section:4,products:['micro-boost-10','cell-renew-1-5','cellular-age-defense-2-5','derma-recovery-cream']},
  {id:'devices',name:'DEVICES',section:5,products:['mitopen','mitoscan']},
  {id:'hair',name:'HAIR',section:6,products:['exosignal-hair','exosignal-spray']},
  {id:'mitotech',name:'MITOTECH',section:0,products:['mitotech-cell-booster']}
];
export const productHref=(slug:string)=>`/products/${slug}`;
