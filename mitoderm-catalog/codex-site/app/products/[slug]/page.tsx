import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {products} from '@/mitoderm/data';
import ProductCinema from '@/mitoderm/pilot/ProductCinema';
import VTech from '@/mitoderm/pilot/VTech';

type Props={params:Promise<{slug:string}>};
export function generateStaticParams(){return products.map(product=>({slug:product.slug}));}

export async function generateMetadata({params}:Props):Promise<Metadata>{
 const {slug}=await params;
 const product=products.find(item=>item.slug===slug);
 if(!product)notFound();
 const title=product.name+' | MITODERM';
 const description=product.intro.body;
 const url='/products/'+product.slug;
 return {
  title:product.name,description,alternates:{canonical:url},
  openGraph:{title,description,url,type:'website',locale:'he_IL',siteName:'MITODERM',images:[{url:'/assets/brand/og.webp',alt:product.name+' — MITODERM'}]},
  twitter:{card:'summary_large_image',title,description,images:['/assets/brand/og.webp']},
 };
}

export default async function ProductPage({params}:Props){
 const {slug}=await params;
 const product=products.find(item=>item.slug===slug);
 if(!product)notFound();
 return product.slug==='v-tech-system'?<VTech/>:<ProductCinema product={product}/>;
}
