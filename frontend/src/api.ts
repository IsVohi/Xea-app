/**
 * Xea Governance Oracle - API Client
 * 
 * TypeScript client for interacting with the backend API.
 */

import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Types matching the backend schemas
export interface Claim {
    id: string;
    text: string;
    paragraph_index: number;
    char_range: [number, number];
    type: 'factual' | 'mathematical' | 'temporal' | 'comparative' | 'procedural' | 'conditional';
    canonical: string;
}

export interface MinerScores {
    accuracy: number;
    omission_risk: number;
    evidence_quality: number;
    governance_relevance: number;
    composite: number;
}

export interface MinerResponse {
    miner_id: string;
    claim_id: string;
    verdict: 'verified' | 'refuted' | 'unverifiable' | 'partial';
    rationale: string;
    evidence_links: string[];
    embedding?: number[];
    scores: MinerScores;
}

export interface IngestRequest {
    url?: string;
    text?: string;
}

export interface IngestResponse {
    proposal_hash: string;
    canonical_text: string;
    claims: Claim[];
}

export interface ValidateRequest {
    proposal_hash: string;
}

export interface ValidateResponse {
    job_id: string;
    proposal_hash: string;
    status: 'queued' | 'running' | 'completed' | 'failed';
    created_at: string;
    estimated_completion?: string;
}

export interface JobProgress {
    claims_total: number;
    claims_validated: number;
    miners_contacted: number;
    miners_responded: number;
}

export interface StatusResponse {
    job_id: string;
    status: 'queued' | 'running' | 'completed' | 'failed';
    progress: JobProgress;
    partial_results: MinerResponse[];
    started_at?: string;
    updated_at?: string;
    completed_at?: string;
    ready_for_aggregation: boolean;
}

export interface AggregatedMetrics {
    poi_agreement: number;
    poi_confidence_interval: [number, number];
    pouw_score: number;
    pouw_confidence_interval: [number, number];
    total_miners: number;
    responding_miners: number;
    consensus_verdict: 'verified' | 'refuted' | 'unverifiable' | 'partial';
    claim_coverage: number;
}

export interface Recommendation {
    action: 'approve' | 'reject' | 'review';
    confidence: number;
    risk_flags: string[];
    summary: string;
}

export interface EvidenceBundle {
    proposal_hash: string;
    claims: Claim[];
    miners: MinerResponse[];
    aggregated_metrics: AggregatedMetrics;
    recommendation: Recommendation;
    ipfs_cid?: string;
    signature?: string;
}

export interface AttestResponse {
    attestation_id: string;
    evidence_cid: string;
    signature: string;
    signer_address: string;
    tx_hash?: string;
    tx_link?: string;
    status: 'signed' | 'submitted' | 'confirmed';
    created_at: string;
}

class XeaApiClient {
    private client: AxiosInstance;

    constructor(baseURL: string = API_BASE_URL) {
        this.client = axios.create({
            baseURL,
            headers: {
                'Content-Type': 'application/json',
            },
        });
    }

    /**
     * Ingest a proposal from URL or text
     */
    async ingest(request: IngestRequest): Promise<IngestResponse> {
        const response = await this.client.post<IngestResponse>('/ingest', request);
        return response.data;
    }

    /**
     * Start validation job for a proposal
     */
    async validate(request: ValidateRequest): Promise<ValidateResponse> {
        const response = await this.client.post<ValidateResponse>('/validate', request);
        return response.data;
    }

    /**
     * Get status of a validation job
     */
    async getStatus(jobId: string): Promise<StatusResponse> {
        const response = await this.client.get<StatusResponse>(`/status/${jobId}`);
        return response.data;
    }

    /**
     * Aggregate validation results
     */
    async aggregate(jobId: string): Promise<EvidenceBundle> {
        const response = await this.client.post<EvidenceBundle>('/aggregate', { job_id: jobId });
        return response.data;
    }

    /**
     * Create attestation for evidence bundle
     */
    async attest(evidenceCid: string): Promise<AttestResponse> {
        const response = await this.client.post<AttestResponse>('/attest', {
            evidence_cid: evidenceCid,
        });
        return response.data;
    }

    /**
     * Health check
     */
    async health(): Promise<{ status: string; version: string }> {
        const response = await this.client.get('/health');
        return response.data;
    }
}

export const api = new XeaApiClient();
export default api;
