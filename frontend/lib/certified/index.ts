/**
 * The certification registry: one data file, empty at launch. Every issued badge gets a
 * short record id and a page at /certified/<id>, generated statically from this file.
 * The export must build with zero records, and the registry then says that no agent is
 * certified yet. Records are added only by Suncly, by hand, from a signed evaluation.
 */
import records from "./records.json";

export interface CertificationRecord {
  /** Short record id, the badge's link target. */
  id: string;
  agentName: string;
  operator: string;
  agentVersion: string;
  cardHash: string;
  a2aVersion: string;
  sandboxEndpoint: string;
  evaluatedOn: string;
  validUntil: string;
  criteriaVersion: string;
  runs: { testCases: number; perTestCase: number; pass: number; fail: number; inconclusive: number };
  notTested: string[];
  decidedBy: string;
  status: "valid" | "expired" | "suspended" | "revoked";
}

export const certificationRecords: CertificationRecord[] = records as CertificationRecord[];
export const recordById = (id: string) => certificationRecords.find((r) => r.id === id);
