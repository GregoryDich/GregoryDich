import urls from './media-urls.json';
export function mediaUrl(path:string):string{return (urls as Record<string,string>)[path]??path;}
