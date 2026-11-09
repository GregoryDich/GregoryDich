import type {Metadata,Viewport} from 'next';
import type {ReactNode} from 'react';
import {SiteExperience} from '@/mitoderm/pilot/Experience';
import './globals.css';

const origin='https://mitoderm-cinematic.evenradish1.chatgpt.site';
const description='מוצרים מקצועיים לעור ולקרקפת, טיפוח ביתי משלים ומכשור לקליניקות. הכירו את MITODERM וקבלו ייעוץ והצעה מקצועית.';

export const metadata:Metadata={
 metadataBase:new URL(origin),
 title:{default:'MITODERM',template:'%s | MITODERM'},
 description,
 authors:[{name:'MITODERM'}],
 openGraph:{title:'MITODERM',description,type:'website',locale:'he_IL',siteName:'MITODERM',images:[{url:'/assets/brand/og.webp',alt:'MITODERM'}]},
 twitter:{card:'summary_large_image',title:'MITODERM',description,images:['/assets/brand/og.webp']},
 icons:{icon:[{url:'/assets/brand/favicon.ico'},{url:'/assets/brand/favicon-32.png',type:'image/png',sizes:'32x32'}],apple:'/assets/brand/apple-touch-icon.png'},
 manifest:'/site.webmanifest',
};
export const viewport:Viewport={width:'device-width',initialScale:1,themeColor:'#08080a',colorScheme:'dark'};

export default function RootLayout({children}:Readonly<{children:ReactNode}>){
 return <html lang="he" dir="rtl"><head><link rel="preload" as="font" type="font/ttf" href="/fonts/Rubik-400.ttf" crossOrigin="anonymous"/></head><body><SiteExperience>{children}</SiteExperience></body></html>;
}
