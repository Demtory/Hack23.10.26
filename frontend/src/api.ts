import type { CustomerDetail, CustomerPage, Forecast, ForecastDay, Level, ModelSettings, Snapshot, Summary, User } from './types';
export class ApiError extends Error { constructor(public status:number,message:string,public code?:string){super(message);} }
let epoch=0;
export function changeSession(){epoch++;}
export function sessionEpoch(){return epoch;}
async function requestResponse(path:string,init:RequestInit={}){
 const generation=epoch;const headers=new Headers(init.headers);headers.set('Content-Type','application/json');const token=localStorage.getItem('auth_token');if(token)headers.set('Authorization',`Bearer ${token}`);
 const response=await fetch(path,{...init,credentials:'include',headers});
 if(generation!==epoch)throw new DOMException('Сессия изменилась','AbortError');
 if(!response.ok){let message=response.statusText,code;try{const body=await response.json();code=body.detail?.code;message=typeof body.detail==='string'?body.detail:body.detail?.message??(Array.isArray(body.detail)?body.detail.map((e:{loc?:string[];msg:string})=>`${e.loc?.slice(1).join('.')}: ${e.msg}`).join('; '):'Не удалось выполнить операцию');}catch{/* response may have no JSON */}
 if(response.status===401&&!path.endsWith('/auth/login'))window.dispatchEvent(new Event('risk:unauthorized'));
 throw new ApiError(response.status,message,code);}
 return response;
}
async function request<T>(path:string,init:RequestInit={}):Promise<T>{const r=await requestResponse(path,init);return r.status===204?undefined as T:r.json();}
export interface CustomerQuery {sort:string;order:string;level?:Level|'';q?:string;urgency?:'all'|'expired'|'48h'|'7d';page:number;pageSize:number;}
function params(query:CustomerQuery){const p=new URLSearchParams({sort:query.sort,order:query.order,page:String(query.page),pageSize:String(query.pageSize),urgency:query.urgency??'all'});if(query.level)p.set('level',query.level);if(query.q?.trim())p.set('q',query.q.trim());return p;}
export const api={
 me:()=>request<User>('/api/v1/auth/me'),
 oidcConfig:()=>request<{enabled:boolean;providerName:string}>('/api/v1/auth/oidc/config'),
 login:async(email:string,password:string)=>{const u=await request<User&{token:string}>('/api/v1/auth/login',{method:'POST',body:JSON.stringify({email,password})});changeSession();if(u.token)localStorage.setItem('auth_token',u.token);return u;},
 logout:async()=>{const result=await request<{ok:boolean}>('/api/v1/auth/logout',{method:'POST'});localStorage.removeItem('auth_token');changeSession();return result;},
 customers:(q:CustomerQuery)=>request<CustomerPage>('/api/v1/customers?'+params(q)),
 customer:async(id:number):Promise<CustomerDetail>=>{const r=await requestResponse(`/api/v1/customers/${id}`);const d=await r.json();d.asOf=r.headers.get('X-Calculation-As-Of')??undefined;d.updatedAt=r.headers.get('X-Calculation-Updated-At')??undefined;return d;},
 summary:()=>request<Summary>('/api/v1/analytics/summary'), forecast:(bucketDays=1)=>request<Forecast>(`/api/v1/analytics/forecast?bucketDays=${bucketDays}`),
 forecastDay:(date:string,end:string,kind:'fact'|'forecast')=>request<ForecastDay>(`/api/v1/analytics/forecast/day?date=${encodeURIComponent(date)}&end=${encodeURIComponent(end)}&kind=${kind}`), settings:()=>request<ModelSettings>('/api/v1/model/settings'),
 updateSettings:(payload:Partial<ModelSettings>&{expectedVersion?:number})=>request<{settings:ModelSettings;summary:Summary}>('/api/v1/model/settings',{method:'PATCH',body:JSON.stringify(payload)}),
 source:()=>request<Snapshot>('/api/v1/source/snapshot'),
 sourceText:async()=>{const r=await requestResponse('/api/v1/source/snapshot');return r.text();},
 sourceView:async()=>{const r=await requestResponse('/api/v1/source/snapshot');return{text:await r.text(),asOf:r.headers.get('X-Calculation-As-Of'),updatedAt:r.headers.get('X-Calculation-Updated-At'),runId:Number(r.headers.get('X-Calculation-Run-Id'))};},
 replaceSourceText:(text:string)=>request<{counts:Record<string,number>;summary:Summary}>('/api/v1/source/snapshot',{method:'PUT',body:text}),
 replaceSource:(snapshot:Snapshot)=>request<{counts:Record<string,number>;summary:Summary}>('/api/v1/source/snapshot',{method:'PUT',body:JSON.stringify(snapshot)}),
 export:async(q:CustomerQuery,runId:number)=>{const p=params(q);p.delete('page');p.delete('pageSize');p.set('runId',String(runId));const r=await requestResponse('/api/v1/customers/export.csv?'+p);return{blob:await r.blob(),filename:`customers-run-${runId}.csv`};},
};
