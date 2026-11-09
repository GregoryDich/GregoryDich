import type {Metadata} from 'next';
import {Catalog} from '@/mitoderm/Home';
export const metadata:Metadata={title:'קטלוג מוצרים',description:'כל 13 מוצרי MITODERM: מערכות מקצועיות, טיפוח משלים ומכשור לקליניקה.',alternates:{canonical:'/catalog'}};
export default function CatalogPage(){return <Catalog/>;}
