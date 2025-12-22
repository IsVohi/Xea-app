import React from 'react';
import { Claim, MinerResponse } from '../api';
import { ClaimRow } from './ClaimRow';

interface ClaimsTableProps {
    claims: Claim[];
    claimStatuses: Map<string, 'pending' | 'validating' | 'completed'>;
    minerResponses: Map<string, MinerResponse[]>;
    totalMiners: number;
}

export function ClaimsTable({ claims, claimStatuses, minerResponses, totalMiners }: ClaimsTableProps) {
    if (claims.length === 0) {
        return (
            <div className="card text-center text-gray-400 py-8">
                No claims extracted yet
            </div>
        );
    }

    return (
        <div className="card">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                    Extracted Claims ({claims.length})
                </h3>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-gray-600" />
                        Pending
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-xea-accent animate-pulse" />
                        Validating
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-verdict-supported" />
                        Completed
                    </span>
                </div>
            </div>

            <div className="space-y-3">
                {claims.map((claim) => {
                    const status = claimStatuses.get(claim.id) || 'pending';
                    const responses = minerResponses.get(claim.id) || [];
                    return (
                        <ClaimRow
                            key={claim.id}
                            claim={claim}
                            status={status}
                            minerCount={responses.length}
                            totalMiners={totalMiners}
                        />
                    );
                })}
            </div>
        </div>
    );
}

export default ClaimsTable;
