#!/usr/bin/env node
// Build a compact Expected-only research payload from independently audited inputs.
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';
import {expectedPayload} from './a1_expected_payload.mjs';

const [fixturePath, fixtureAuditPath, probePath, summaryAuditPath, outputPath, reportPath] = process.argv.slice(2);
if (!fixturePath || !fixtureAuditPath || !probePath || !summaryAuditPath || !outputPath || !reportPath) {
  throw new Error('Provide fixture, fixture audit, summary probe, summary audit, new payload and new report paths');
}
const hash = data => createHash('sha256').update(data).digest('hex');
const fixtureBytes = readFileSync(fixturePath), fixtureHash = hash(fixtureBytes), fixture = JSON.parse(fixtureBytes);
const fixtureAuditBytes = readFileSync(fixtureAuditPath), fixtureAudit = JSON.parse(fixtureAuditBytes);
const probeBytes = readFileSync(probePath), probe = JSON.parse(probeBytes);
const summaryAuditBytes = readFileSync(summaryAuditPath), summaryAudit = JSON.parse(summaryAuditBytes);
const summaryBytes = readFileSync(probe.summary), summary = JSON.parse(summaryBytes);
if (fixtureAudit.fixture_sha256 !== fixtureHash || fixtureAudit.fixture !== fixturePath
    || fixtureAudit.audit_sha256 !== hash(readFileSync('analysis/a1_branch_browser_fixture_audit.py'))
    || probe.fixture !== fixturePath || probe.fixture_sha256 !== fixtureHash || probe.summary_sha256 !== hash(summaryBytes)
    || summaryAudit.probe !== probePath || summaryAudit.probe_sha256 !== hash(probeBytes)
    || summaryAudit.summary_sha256 !== probe.summary_sha256
    || summaryAudit.audit_sha256 !== hash(readFileSync('analysis/a1_branch_game_summary_audit.py'))
    || summaryAudit.selected_worlds !== probe.selected_worlds || summaryAudit.selected_mass !== probe.selected_mass
    || !summaryAudit.distributions_checked || !summaryAudit.means_checked) {
  throw new Error('Audited fixture or summary provenance does not match');
}
const output = JSON.stringify(expectedPayload(fixture, summary, fixtureHash));
writeFileSync(outputPath, output, {flag: 'wx'});
writeFileSync(reportPath, JSON.stringify({
  kind: 'isolated Expected-only serialization probe; not a phone or browser benchmark',
  fixture: fixturePath, fixture_sha256: fixtureHash, fixture_audit: fixtureAuditPath,
  fixture_audit_sha256: hash(fixtureAuditBytes), summary_probe: probePath, summary_probe_sha256: hash(probeBytes),
  summary_audit: summaryAuditPath, summary_audit_sha256: hash(summaryAuditBytes),
  payload: outputPath, payload_sha256: hash(output), payload_bytes: Buffer.byteLength(output),
  gzip6_bytes: gzipSync(output, {level: 6}).length,
  algorithm_sha256: hash(readFileSync('analysis/a1_expected_payload.mjs')),
  probe_sha256: hash(readFileSync('analysis/a1_expected_payload_probe.mjs')),
}, null, 2) + '\n', {flag: 'wx'});
console.log(`Expected-only payload: ${Buffer.byteLength(output)} bytes; independently audited inputs`);
