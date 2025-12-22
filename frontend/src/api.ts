/**
 * Xea Governance Oracle - API Client
 * 
 * TypeScript client for interacting with the backend API.
 */

import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Types matching the backend schemas

export interface ClaimCanonical {
    numbers: number[];
    addresses: string[];
    urls: string[];
}

export interface Claim {
    id: string;
    text: string;
    paragraph_index: number;
    char_range: [number, number];
    type: 'factual' | 'numeric' | 'temporal' | 'comparative' | 'procedural' | 'conditional';
    canonical: ClaimCanonical;
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

export interface ClaimAggregation {
    id: string;
    text: string;
    poi_agreement: number;
    mode_verdict: string;
    embedding_dispersion: number;
    pouw_mean: number;
    pouw_ci_95: [number, number];
    outliers: string[];
    final_recommendation: 'supported' | 'disputed' | 'supported_with_caution';
    miner_responses: MinerResponse[];
}

export interface EvidenceBundle {
    proposal_hash: string;
    job_id: string;
    claims: ClaimAggregation[];
    overall_poi_agreement: number;
    overall_pouw_score: number;
    overall_ci_95: [number, number];
    critical_flags: string[];
    timestamp: string;
}

export interface AggregateRequest {
    job_id: string;
    publish?: boolean;
}

export interface AggregateResponse {
    job_id: string;
    evidence_bundle: EvidenceBundle;
    ipfs_cid?: string;
}

export interface AttestRequest {
    job_id: string;
    publish?: boolean;
}

export interface AttestResponse {
    job_id: string;
    proposal_hash: string;
    ipfs_cid?: string;
    signature: string;
    signer: string;
    message_hash: string;
    verification_instructions: {
        step_1: string;
        step_2: string;
        step_3: string;
        step_4: string;
    };
}

// WebSocket message types
export interface WSMinerResponseMessage {
    type: 'miner_response';
    job_id: string;
    claim_id: string;
    miner_id: string;
    verdict: string;
    timestamp: string;
}

export interface WSStatusMessage {
    type: 'status';
    job_id: string;
    status: string;
    progress: JobProgress;
}

export interface WSAggregateMessage {
    type: 'aggregate';
    job_id: string;
    evidence_bundle: EvidenceBundle;
}

export type WSMessage = WSMinerResponseMessage | WSStatusMessage | WSAggregateMessage;

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
     * Aggregate validation results into evidence bundle
     */
    async aggregate(request: AggregateRequest): Promise<AggregateResponse> {
        const response = await this.client.post<AggregateResponse>('/aggregate', request);
        return response.data;
    }

    /**
     * Create attestation for evidence bundle
     */
    async attest(request: AttestRequest): Promise<AttestResponse> {
        const response = await this.client.post<AttestResponse>('/attest', request);
        return response.data;
    }

    /**
     * Get evidence bundle by job ID
     */
    async getEvidence(jobId: string): Promise<EvidenceBundle> {
        const response = await this.client.get<EvidenceBundle>(`/evidence/${jobId}`);
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
export const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');
export default api;
