import type {MetadataRoute} from 'next';
import {products} from '@/mitoderm/data';
import {SITE_ORIGIN} from '@/mitoderm/site';

export default function sitemap():MetadataRoute.Sitemap{
 return ['/','/catalog',...products.map(product=>'/products/'+product.slug),'/privacy'].map(path=>({url:SITE_ORIGIN+path}));
}
