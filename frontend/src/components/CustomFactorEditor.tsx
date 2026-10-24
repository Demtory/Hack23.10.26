import {useState} from 'react';
import type {CustomFactor,ModelSettings} from '../types';
const fields:Record<CustomFactor['field'],string>={daysToExpiry:'Дней до окончания услуги',price:'Цена продления, €',balance:'Основной баланс, €',totalReplenished:'Всего пополнено, €',autoProlong:'Автопродление',status:'Статус услуги'};
const statuses:Record<string,string>={active:'Работает',suspended:'Выключена',blocked:'Заблокирована',prolong_wait:'Ожидает оплаты'};
export function CustomFactorEditor({draft,onChange}:{draft:ModelSettings;onChange:(s:ModelSettings)=>void}){
 const [open,setOpen]=useState(false);
 const [editing,setEditing]=useState<string|null>(null);
 const [rule,setRule]=useState<Omit<CustomFactor,'code'>>({title:'',field:'daysToExpiry',operator:'lte',value:3,risk:100});
 const rules=draft.customFactors??[];
 function add(){
  if(!rule.title.trim())return;
  const code=editing??('custom_'+crypto.randomUUID().replaceAll('-',''));
  const factor={...rule,title:rule.title.trim(),code};
  const feature={code,title:factor.title,description:'Собственное правило: при выполнении условия заданная оценка, иначе 0.',min:0,max:1,step:.01,default:0};
  onChange({...draft,
    customFactors:editing?rules.map(r=>r.code===code?factor:r):[...rules,factor],
    weights:editing?draft.weights:{...draft.weights,[code]:0},
    features:editing?draft.features.map(f=>f.code===code?feature:f):[...draft.features,feature]});
  setOpen(false);setEditing(null);setRule({...rule,title:''});
 }
 function remove(code:string){if(editing===code){setEditing(null);setOpen(false);}const weights={...draft.weights};delete weights[code];onChange({...draft,customFactors:rules.filter(r=>r.code!==code),weights,features:draft.features.filter(f=>f.code!==code)});}
 return <section className="card"><div className="card__heading"><div><p className="card__label">Ваши правила</p><h2>Собственные факторы риска</h2></div><button className="button" disabled={!open&&rules.length>=20} onClick={()=>{setEditing(null);setOpen(!open);setRule({title:'',field:'daysToExpiry',operator:'lte',value:3,risk:100});}}>{open?'Закрыть':'Добавить фактор'}</button></div>
 <p className="muted">Выберите условие и оценку от 0 до 100. Если условие не выполнено, оценка фактора — 0. Новый фактор создаётся с влиянием 0: включите его ниже и сохраните настройки. Максимум — 20 правил.</p>
 {rules.map(r=><div className="custom-rule" key={r.code}><div><strong>{r.title}</strong><p>{fields[r.field]} {({lt:'<',lte:'≤',eq:'=',gte:'≥',gt:'>'})[r.operator]} {typeof r.value==='boolean'?(r.value?'включено':'отключено'):statuses[String(r.value)]??String(r.value)} → {r.risk} из 100</p></div><button className="button" aria-label={`Изменить фактор ${r.title}`} onClick={()=>{const {code,...value}=r;setRule(value);setEditing(code);setOpen(true);}}>Изменить</button><button className="button" onClick={()=>remove(r.code)} aria-label={`Удалить фактор ${r.title}`}>Удалить</button></div>)}
 {open&&<div className="custom-rule-form">
 <label className="field"><span>Название фактора</span><input maxLength={80} value={rule.title} onChange={e=>setRule({...rule,title:e.target.value})}/></label>
 <label className="field"><span>Поле</span><select value={rule.field} onChange={e=>{const field=e.target.value as CustomFactor['field'];setRule({...rule,field,operator:field==='status'||field==='autoProlong'?'eq':'lte',value:field==='status'?'active':field==='autoProlong'?false:0});}}>{Object.entries(fields).map(([v,t])=><option value={v} key={v}>{t}</option>)}</select></label>
 <label className="field"><span>Условие</span><select value={rule.operator} onChange={e=>setRule({...rule,operator:e.target.value as CustomFactor['operator']})}>{Object.entries({lt:'Меньше',lte:'Не больше',eq:'Равно',gte:'Не меньше',gt:'Больше'}).filter(([v])=>!['status','autoProlong'].includes(rule.field)||v==='eq').map(([v,t])=><option value={v} key={v}>{t}</option>)}</select></label>
 <label className="field"><span>Значение</span>{rule.field==='status'?<select value={String(rule.value)} onChange={e=>setRule({...rule,value:e.target.value})}>{Object.entries(statuses).map(([v,t])=><option value={v} key={v}>{t}</option>)}</select>:rule.field==='autoProlong'?<select value={String(rule.value)} onChange={e=>setRule({...rule,value:e.target.value==='true'})}><option value="true">Включено</option><option value="false">Отключено</option></select>:<input type="number" step="any" value={Number(rule.value)} onChange={e=>setRule({...rule,value:Number(e.target.value)})}/>}</label>
 <label className="field"><span>Оценка при выполнении, 0–100</span><input type="number" min={0} max={100} value={rule.risk} onChange={e=>setRule({...rule,risk:Number(e.target.value)})}/></label>
 <button className="button button--primary" disabled={!rule.title.trim()||!Number.isFinite(rule.risk)||rule.risk<0||rule.risk>100} onClick={add}>{editing?'Обновить в черновике':'Добавить в черновик'}</button>
 </div>}</section>;
}
