import { describe, it, expect } from 'vitest';
import { labels, recordView, errorMessages, textError, displayDate } from '../src/api/presentation';
import examples from '../src/api/scenarios.json';
import type { CheckRecord } from '../src/api/client';
describe('contract presentation',()=>{
 it('keeps exactly three verdicts, without mapping technical failures to NEI',()=>{
  expect(Object.keys(labels)).toEqual(['supported','contradicted','insufficient_evidence']);
  expect(labels.supported).toBe('Được nguồn hỗ trợ');
  expect(labels.contradicted).toBe('Mâu thuẫn với nguồn');
  expect(labels.insufficient_evidence).toBe('Chưa đủ bằng chứng');
  expect(recordView(examples.nei as CheckRecord)).toBe('result');
  expect(recordView(examples.failed as CheckRecord)).toBe('error');
  expect(recordView({...examples.failed,status:'retrieving',error:null} as CheckRecord)).toBe('progress');
 });
 it('maps unavailable corpus to a technical recovery message, not missing evidence',()=>{
  expect(errorMessages.CORPUS_UNAVAILABLE).toContain('không truy cập');
  expect(errorMessages.PROVIDER_TIMEOUT).toContain('thử lại');
  expect(errorMessages.RESOURCE_EXPIRED).toContain('bắt đầu lại');
  expect(Object.keys(errorMessages)).toHaveLength(16);
 });
 it('preserves supported historical amount independently of expiry',()=>{
  const claim=examples.expired.result!.claims[0]!;
  expect(claim.label).toBe('supported');expect(claim.temporal_status).toBe('expired');
 });
 it('validates NFC code point length and explicit consent',()=>{
  expect(textError('',false)).toContain('20');
  expect(textError('a'.repeat(6001),true)).toContain('6.000');
  expect(textError('a'.repeat(20),false)).toContain('xác nhận');
  expect(textError('a'.repeat(20),true)).toBeNull();
  expect(textError('ế'.normalize('NFD').repeat(20),true)).toBeNull();
 });
 it('keeps date-only values date-only and timestamps in Vietnam time',()=>{
  expect(displayDate('2026-11-01')).toBe('01/11/2026');
  expect(displayDate('2026-11-08T10:00:00Z')).toContain('17:00');
 });
});
