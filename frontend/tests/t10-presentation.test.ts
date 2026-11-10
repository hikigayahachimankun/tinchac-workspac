import { expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { ResultTable, modeNames } from '../src/components/ResultTable';
import { sourceLink } from '../src/components/EvidencePanel';
import { displayDate, recordView } from '../src/api/presentation';
import { createMockClient } from '../src/api/client';
import type { Schema, CheckRecord } from '../src/api/client';
import example from '../../contracts/examples/check_result.json';
import source from '../../contracts/examples/SourcePublic.json';

it('renders all contract modes, temporal independently and backend next_steps as escaped text',()=>{
 for(const mode of ['fixture','replay','live'] as const) {
  const result=structuredClone(example.result) as Schema['CheckResult'];
  result.run_mode=mode;result.claims[0]!.temporal_status='expired';
  result.warnings=['<img src=x onerror=alert(1)>'];
  result.next_steps=['https://unconfirmed.example/pay','<script>alert(1)</script>'];
  const html=renderToStaticMarkup(createElement(ResultTable,{result,client:createMockClient('original')}));
  expect(html).toContain(modeNames[mode]);expect(html).toContain('Đã hết hạn');
  expect(html).toContain('Mâu thuẫn với nguồn');expect(html).toContain('hết hạn không chứng minh giả mạo');
  expect(html).toContain('&lt;script&gt;');expect(html).not.toContain('<script>');
  expect(html).not.toContain('href="https://unconfirmed');expect(html).toContain('&lt;img');
 }
});
it('all-N with no citations still shows corpus scope, date and backend next steps',()=>{
 const result=structuredClone(example.result) as Schema['CheckResult'];
 result.sources=[];result.claims=result.claims.map(c=>({...c,label:'insufficient_evidence',evidence:[]}));
 result.summary={supported:0,contradicted:0,insufficient_evidence:result.claims.length,message:'Chưa đủ bằng chứng'};
 const html=renderToStaticMarkup(createElement(ResultTable,{result,client:createMockClient('original')}));
 expect(html).toContain(result.corpus_version);expect(html).toContain('không có nghĩa là thông báo sai');
 for(const step of result.next_steps) expect(html).toContain(step);
 expect(recordView({...example,status:'failed'} as CheckRecord)).toBe('error');
 expect(recordView({...example,status:'completed'} as CheckRecord)).toBe('result');
});
it('only canonical http(s) URLs from public sources become links; fixture and credentials are inert',()=>{
 for(const url of ['javascript:alert(1)','data:text/html,x','file:///etc/passwd','/relative','https://user:pass@dut.udn.vn/']) {
  expect(sourceLink({...source,is_fixture:false,canonical_url:url})).toBeNull();
 }
 expect(sourceLink(source)).toBeNull();
 expect(sourceLink({...source,is_fixture:false,canonical_url:'https://dut.udn.vn/notice?id=1'})).toBe('https://dut.udn.vn/notice?id=1');
});
it('preserves date-only precision and formats timestamp in UTC+7',()=>{
 expect(displayDate('2026-11-10')).toBe('10/11/2026');
 expect(displayDate('2026-11-10T18:30:00Z')).toContain('11/11/26');
 expect(displayDate('2026-11-10T18:30:00Z')).toContain('01:30');
});
