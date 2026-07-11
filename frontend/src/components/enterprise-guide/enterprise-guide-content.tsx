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
    <div className="max-w-3xl mx-auto w-full px-6 py-5 space-y-5">
      <div data-section="overview">
        <ExecutiveSummaryHeader data={guide.repository_health} />
      </div>

      <div data-section="ai-summary">
        <AiExecutiveSummarySection
          summary={guide.ai_executive_summary}
          jobId={guide.job_id}
        />
      </div>

      <div data-section="scorecards">
        <EngineeringScorecards data={guide.engineering_scorecard} />
      </div>

      <div data-section="effort">
        <EstimatedEffortSummary data={guide.estimated_effort} />
      </div>

      <div data-section="risk">
        <BusinessRiskSection data={guide.business_risk} />
      </div>

      <div data-section="debt">
        <TechnicalDebtSection data={guide.technical_debt} />
      </div>

      <div data-section="clusters">
        <IssueClusterSection clusters={guide.issue_clusters} />
      </div>

      <div data-section="hotspots">
        <HotspotsSection hotspots={guide.hotspots} />
      </div>

      <div data-section="health">
        <ServiceHealthSection data={guide.service_health} />
      </div>

      <div data-section="quick-wins">
        <QuickWinsSection data={guide.quick_wins} />
      </div>

      <div data-section="scalability">
        <ScalabilityReviewSection data={guide.scalability_review} />
      </div>

      <div data-section="deployment">
        <DeploymentReleaseSection
          deployment={guide.deployment_readiness}
          release={guide.release_recommendation}
        />
      </div>

      <div data-section="roadmap">
        <SprintRoadmapSection data={guide.sprint_roadmap} />
      </div>

      <div data-section="ownership">
        <OwnershipSection data={guide.ownership} />
      </div>

      <div data-section="ai-recs">
        <AIRecommendationsSection data={guide.ai_recommendations} />
      </div>
    </div>
  );
}
