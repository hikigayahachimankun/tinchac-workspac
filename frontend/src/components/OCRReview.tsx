import { useEffect, useRef, useState } from 'react';
import type { AssetClient, Schema } from '../api/client';
import { POLL_MS, POLL_LIMIT_MS } from '../api/client';
import { textError } from '../api/presentation';

export type ImageConfirmation = {asset_id:string;asset_token:string};
export function OCRReview({client,busy,onConfirm}: {
 client:AssetClient;busy:boolean;onConfirm:(text:string,asset?:ImageConfirmation)=>void;
}) {
 const [preview,setPreview]=useState('');
 const [text,setText]=useState('');
 const [record,setRecord]=useState<Schema['AssetRecord']|null>(null);
 const [working,setWorking]=useState(false);
 const [slow,setSlow]=useState(false);
 const [message,setMessage]=useState('');
 const [error,setError]=useState('');
 const [consent,setConsent]=useState(false);
 const generation=useRef(0);
 const edited=useRef(false);
 const session=useRef<ImageConfirmation|null>(null);
 const input=useRef<HTMLTextAreaElement>(null);
 const locked=busy||working;
 useEffect(()=>()=>{
   generation.current++;
   const asset=session.current;
   if(asset) void client.deleteAsset(asset.asset_id,asset.asset_token).catch(()=>{});
 },[client]);
 useEffect(()=>()=>{if(preview) URL.revokeObjectURL(preview);},[preview]);
 async function poll(asset:ImageConfirmation, version:number) {
   const started=Date.now();
   while(generation.current===version && Date.now()-started<POLL_LIMIT_MS) {
     await new Promise(resolve=>setTimeout(resolve,POLL_MS));
     if(generation.current!==version) return;
     const next=await client.getAsset(asset.asset_id,asset.asset_token);
     if(generation.current!==version) return;
     setRecord(next);
     if(next.status==='ready'||next.status==='failed') {
       if(!edited.current) setText(next.ocr?.text??'');
       setWorking(false);setSlow(false);
       setMessage(next.error?.message??(!next.ocr?.text?'Không đọc được chữ; hãy nhập tay.':[next.ocr.low_quality?'Chất lượng OCR thấp; kiểm tra kỹ chữ trước khi xác nhận.':'',...next.ocr.warnings].filter(Boolean).join(' ')));
       input.current?.focus();return;
     }
   }
   if(generation.current===version) {setWorking(false);setSlow(true);setMessage('OCR đang xử lý lâu. Kiểm tra lại hoặc nhập tay để kiểm tra văn bản.');}
 }
 async function upload(file?:File) {
   if(!file) return;
   const version=++generation.current;edited.current=false;
   const previous=session.current;session.current=null;
   if(previous) void client.deleteAsset(previous.asset_id,previous.asset_token).catch(()=>{});
   setRecord(null);setText('');setConsent(false);setError('');setSlow(false);setMessage('');setPreview('');
   if(!['image/png','image/jpeg'].includes(file.type)||file.size>5242880) {setError('Chọn PNG/JPEG tối đa 5 MiB, 12 megapixel.');return;}
   setPreview(URL.createObjectURL(file));setWorking(true);
   try {
     const created=await client.createAsset(file);
     const asset={asset_id:created.asset.asset_id,asset_token:created.access_token};
     if(generation.current!==version) {void client.deleteAsset(asset.asset_id,asset.asset_token).catch(()=>{});return;}
     session.current=asset;setRecord(created.asset);
     await poll(asset,version);
   } catch {
     if(generation.current===version) {setWorking(false);setSlow(!!session.current);setMessage('Không xử lý được ảnh. Bạn có thể nhập tay; nội dung sẽ được gửi theo luồng văn bản.');}
   }
 }
 return <section className="ocr-section" aria-labelledby="ocr-title"><h1 id="ocr-title">Kiểm tra chữ từ ảnh</h1>
   <p className="hint" id="upload-hint">Che thông tin cá nhân trước khi tải. PNG/JPEG tối đa 5 MiB, 12 megapixel. Ảnh chỉ OCR cục bộ, không gửi sang model.</p>
   <label htmlFor="image-file">Chọn ảnh thông báo</label><input id="image-file" type="file" accept="image/png,image/jpeg" disabled={locked} aria-describedby="upload-hint" onChange={e=>void upload(e.target.files?.[0])}/>
   {working&&<><p role="status">Đang đọc chữ từ ảnh…</p><button type="button" disabled={busy} onClick={()=>{
     ++generation.current;const asset=session.current;session.current=null;setRecord(null);setWorking(false);setSlow(false);
     setMessage('Đã dừng OCR. Bạn có thể nhập tay để kiểm tra văn bản.');
     if(asset) void client.deleteAsset(asset.asset_id,asset.asset_token).catch(()=>setMessage('Đã dừng OCR; chưa xác nhận xóa ảnh trên máy chủ. Ảnh còn lại được dọn theo thời hạn lưu.'));
   }}>Dừng OCR và nhập tay</button></>}
   {message&&<p role="status" className="hint">{message}</p>}
   {slow&&<button disabled={locked} onClick={()=>{if(session.current){setWorking(true);setSlow(false);void poll(session.current,generation.current).catch(()=>{setWorking(false);setMessage('Không đọc được trạng thái OCR; hãy nhập tay.');});}}}>Kiểm tra lại OCR</button>}
   {preview&&<div className="ocr-grid"><img className="ocr-preview" src={preview} alt="Ảnh thông báo bạn đã chọn, xem trước trên thiết bị"/>
    <form noValidate onSubmit={event=>{event.preventDefault();const problem=textError(text,consent);setError(problem??'');if(problem){input.current?.focus();return;}onConfirm(text.normalize('NFC').trim(),record?.status==='ready'?session.current??undefined:undefined);}}>
     <label htmlFor="ocr-text">Chữ để đối chiếu (có thể sửa hoặc nhập tay)</label>
     <p className="hint" id="ocr-hint">Kiểm tra kỹ số tiền và ngày. Chỉ gửi kiểm tra sau khi bạn xác nhận. {record?.status==='failed'||(!working&&record?.status!=='ready')?'Nhập tay sẽ dùng luồng văn bản.':''}</p>
     <textarea ref={input} id="ocr-text" rows={9} value={text} disabled={locked} onChange={e=>{edited.current=true;setText(e.target.value);setError('');}} aria-describedby="ocr-hint"/>
     <label className="consent"><input type="checkbox" checked={consent} disabled={locked} onChange={e=>setConsent(e.target.checked)}/>Tôi đã kiểm tra chữ, che thông tin cá nhân và đồng ý xử lý.</label>
     {error&&<p role="alert" className="form-error">{error}</p>}
     <button type="submit" className="primary" disabled={locked}>Xác nhận chữ và kiểm tra</button>
    </form></div>}
   {!preview&&error&&<p role="alert" className="form-error">{error}</p>}
 </section>;
}
