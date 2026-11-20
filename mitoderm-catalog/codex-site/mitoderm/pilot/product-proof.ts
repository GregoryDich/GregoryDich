// Real before/after photographs of the brand's own patients, supplied by the
// owner. The files are hosted and resolved through media-urls.json: photos of
// people are never kept in the repository. Nothing is drawn on the photos.
export type ProofPair={before:string;after:string};
const pairs=(slug:string,count:number):ProofPair[]=>Array.from({length:count},(_,i)=>({
 before:`/assets/proof/${slug}-${i+1}-before.jpg`,
 after:`/assets/proof/${slug}-${i+1}-after.jpg`
}));
export const productProof:Record<string,ProofPair[]>={
 'exosignal-hair':pairs('exosignal-hair',3)
};
