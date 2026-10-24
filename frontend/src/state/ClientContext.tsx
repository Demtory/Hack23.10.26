import {createContext,useContext,useState,ReactNode} from 'react';
import type {CustomerQuery} from '../api';
export const defaults:CustomerQuery={sort:'score',order:'desc',level:'',q:'',urgency:'all',page:1,pageSize:10};
export interface RestorePoint{selection:CustomerQuery;scrollY:number;tableScrollLeft:number;focusId?:number;owner:string;}
const Context=createContext<ReturnType<typeof useValue>|null>(null);
function useValue(){const[selection,setSelection]=useState({...defaults});const[restore,setRestore]=useState<RestorePoint|null>(null);return{selection,setSelection,restore,setRestore};}
export function ClientProvider({children}:{children:ReactNode}){return <Context.Provider value={useValue()}>{children}</Context.Provider>;}
export function useClients(){return useContext(Context)!;}
