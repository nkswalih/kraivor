'use client';

import type { EnterpriseGuide } from '@/types/domain/analysis';
import { AiExecutiveSummarySection } from '@/components/analysis/enterprise-guide/AiExecutiveSummarySection';
import {
  ExecutiveSummaryHeader,
  EngineeringScorecards,
  EstimatedEffortSummary,
} from './sections/executive';
import {
  BusinessRiskSection,
  TechnicalDebtSection,
  IssueClusterSection,
  HotspotsSection,
  ScalabilityReviewSection,
} from './sections/risk-clusters';
import {
  SprintRoadmapSection,
  OwnershipSection,
  AIRecommendationsSection,
  QuickWinsSection,
  ServiceHealthSection,
  DeploymentReleaseSection,
} from './sections/roadmap-ownership';

export function EnterpriseGuideContent({ guide }: { guide: EnterpriseGuide }) {
  return (
    <div className="max-w-3xl mx-auto w-full p-6 space-y-5">
      <ExecutiveSummaryHeader data={guide.repository_health} />

      <AiExecutiveSummarySection
        summary={guide.ai_executive_summary}
        jobId={guide.job_id}
      />

      <EngineeringScorecards data={guide.engineering_scorecard} />
      <EstimatedEffortSummary data={guide.estimated_effort} />
      <BusinessRiskSection data={guide.business_risk} />
      <TechnicalDebtSection data={guide.technical_debt} />
      <IssueClusterSection clusters={guide.issue_clusters} />
      <HotspotsSection hotspots={guide.hotspots} />
      <ServiceHealthSection data={guide.service_health} />
      <QuickWinsSection data={guide.quick_wins} />
      <ScalabilityReviewSection data={guide.scalability_review} />
      <DeploymentReleaseSection
        deployment={guide.deployment_readiness}
        release={guide.release_recommendation}
      />
      <SprintRoadmapSection data={guide.sprint_roadmap} />
      <OwnershipSection data={guide.ownership} />
      <AIRecommendationsSection data={guide.ai_recommendations} />
    </div>
  );
}
