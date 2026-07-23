// ─── Enums ──────────────────────────────────────────────

export enum JobStatus {
  QUEUED = 'queued',
  CLONING = 'cloning',
  PARSING = 'parsing',
  RULES = 'rules',
  DEAD_CODE = 'dead_code',
  ERRORS = 'errors',
  PERF = 'perf',
  SIMULATION = 'simulation',
  SCORING = 'scoring',
  GUIDE_GEN = 'guide_gen',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export enum Severity {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  INFO = 'info',
}

export enum Category {
  PERFORMANCE = 'performance',
  SECURITY = 'security',
  RELIABILITY = 'reliability',
  MAINTAINABILITY = 'maintainability',
  DEVOPS = 'devops',
  DEAD_CODE = 'dead_code',
  ERROR = 'error',
  STRUCTURE = 'structure',
  QUALITY = 'quality',
}

export enum DeadCodeType {
  UNUSED_IMPORT = 'unused_import',
  UNUSED_FUNCTION = 'unused_function',
  UNUSED_VARIABLE = 'unused_variable',
  DEAD_ROUTE = 'dead_route',
  ORPHAN_CLASS = 'orphan_class',
  UNREACHABLE_CODE = 'unreachable_code',
  UNUSED_PARAMETER = 'unused_parameter',
  UNUSED_ASSIGNMENT = 'unused_assignment',
}

export enum ErrorType {
  BARE_EXCEPT = 'bare_except',
  SWALLOWED_EXCEPTION = 'swallowed_exception',
  MISSING_TRY = 'missing_try',
  UNHANDLED_EXCEPTION = 'unhandled_exception',
  MISSING_VALIDATION = 'missing_validation',
  MISSING_TIMEOUT = 'missing_timeout',
  SILENT_FAIL = 'silent_fail',
  IMPROPER_ERROR_PROPAGATION = 'improper_error_propagation',
}

export enum SimulationStatus {
  STABLE = 'stable',
  DEGRADED = 'degraded',
  FAILING = 'failing',
}

export enum Tiers {
  PRODUCTION_READY = 'production_ready',
  MINOR_ISSUES = 'minor_issues',
  NEEDS_WORK = 'needs_work',
  SIGNIFICANT_RISK = 'significant_risk',
  CRITICAL_STATE = 'critical_state',
}

// ─── Analysis Job ───────────────────────────────────────

export interface AnalysisJob {
  job_id: string;
  repo_id: string;
  workspace_id: string;
  status: JobStatus;
  repo_url: string;
  branch: string;
  progress_pct: number;
  progress_message: string;
  total_findings: number;
  total_files: number | null;
  total_lines: number | null;
  overall_score: number | null;
  blocked_by: string[];
  engine_statuses: Record<string, string>;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ScoreHistoryEntry {
  time: string;
  overall_score: number;
  performance_score: number | null;
  security_score: number | null;
  reliability_score: number | null;
  maintainability_score: number | null;
  devops_score: number | null;
  findings_count: number;
}

export interface ScoreHistoryListResponse {
  entries: ScoreHistoryEntry[];
  total: number;
}

export interface JobListResponse {
  jobs: AnalysisJob[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Findings ───────────────────────────────────────────

export interface Finding {
  id: string;
  job_id: string;
  rule_id: string;
  category: Category;
  severity: Severity;
  title: string;
  description: string;
  recommendation: string;
  enterprise_pattern: string;
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  status: 'active' | 'dismissed';
  code_snippet: string;
  score_impact: number;
  rpm_impact: number;
  is_ai_enriched: boolean;
}

export interface FindingsListResponse {
  findings: Finding[];
  total: number;
  page: number;
  page_size: number;
}

export interface FindingsSummary {
  job_id: string;
  total: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
}

// ─── Report ─────────────────────────────────────────────

export interface Report {
  job_id: string;
  repo_id: string;
  workspace_id: string;
  branch: string;
  overall_score: number | null;
  performance_score: number | null;
  security_score: number | null;
  reliability_score: number | null;
  maintainability_score: number | null;
  devops_score: number | null;
  total_findings: number;
  total_files: number;
  total_lines_of_code: number;
  languages_detected: string[];
  language_breakdown: { name: string; percentage: number }[];
  duration_seconds: number | null;
  completed_at: string | null;
  report_url: string | null;
}

export interface AnalysisMetadataResponse {
  job_id: string;
  class_count: number;
  function_count: number;
  endpoint_count: number;
  languages: string[];
  frameworks: string[];
}

// ─── Dead Code ──────────────────────────────────────────

export interface DeadCodeFinding {
  id: string;
  code_type: DeadCodeType;
  name: string;
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  context: string | null;
  evidence: string | null;
  confidence: number;
}

export interface DeadCodeListResponse {
  findings: DeadCodeFinding[];
  total: number;
}

// ─── Error Findings ─────────────────────────────────────

export interface ErrorFinding {
  id: string;
  error_type: ErrorType;
  severity: Severity;
  title: string;
  description: string | null;
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  code_snippet: string | null;
  recommendation: string | null;
}

export interface ErrorFindingListResponse {
  findings: ErrorFinding[];
  total: number;
}

// ─── Performance Metrics ────────────────────────────────

export interface PerformanceMetric {
  id: string;
  metric_type: string;
  endpoint: string | null;
  http_method: string | null;
  estimated_rpm: number | null;
  p50_latency_ms: number | null;
  p95_latency_ms: number | null;
  p99_latency_ms: number | null;
  max_concurrent_users: number | null;
  bottleneck_type: string | null;
  bottleneck_severity: string | null;
  bottleneck_detail: string | null;
}

export interface PerformanceMetricListResponse {
  metrics: PerformanceMetric[];
  total: number;
}

// ─── Simulation Results ─────────────────────────────────

export interface SimulationResult {
  id: string;
  concurrent_users: number;
  status: SimulationStatus;
  overall_rpm: number | null;
  error_rate_pct: number | null;
  endpoints_analysis: Record<string, unknown> | null;
  bottlenecks: unknown[] | null;
}

export interface SimulationResultListResponse {
  results: SimulationResult[];
  total: number;
}

// ─── Enterprise Guide ───────────────────────────────────

export interface DimensionHealth {
  score: number | null;
  grade: string | null;
  status: string;
  label?: string;
}

export interface ScorecardCategory {
  score: number | null;
  grade: string | null;
  trend: string;
  industry_comparison: string;
  biggest_problem: string;
  best_recommendation: string;
  total_findings: number;
  severity_breakdown: Record<string, number>;
}

export interface RepositoryHealth {
  overall_score: number | null;
  overall_grade: string | null;
  repository_health: string;
  production_readiness: string;
  deployment_readiness: string;
  release_recommendation: string;
  business_risk: string;
  engineering_risk: string;
  technical_debt_level: string;
  estimated_remediation_time: string;
  estimated_team_size: number | null;
}

export interface BusinessRisk {
  revenue_risk: string;
  customer_impact: string;
  compliance_risk: string;
  reputation_risk: string;
  downtime_risk: string;
  operational_risk: string;
  details: string;
}

export interface ScalabilityReview {
  estimated_rpm: number | null;
  estimated_concurrent_users: number | null;
  expected_bottleneck: string | null;
  database_scalability: { score: number | null; grade: string | null; recommendation: string } | null;
  cache_recommendation: string | null;
  queue_recommendation: string | null;
  horizontal_scaling_readiness: { score: number; grade: string; status: string } | null;
  vertical_scaling_readiness: { score: number; grade: string; status: string } | null;
  infrastructure_cost_projection: string | null;
  status?: string;
}

export interface TechnicalDebt {
  security_debt: { count: number; estimated_minutes: number; estimated_hours: number; severity: string; label: string };
  architecture_debt: { count: number; estimated_minutes: number; estimated_hours: number; severity: string; label: string };
  performance_debt: { count: number; estimated_minutes: number; estimated_hours: number; severity: string; label: string };
  maintainability_debt: { count: number; estimated_minutes: number; estimated_hours: number; severity: string; label: string };
  devops_debt: { count: number; estimated_minutes: number; estimated_hours: number; severity: string; label: string };
  other_debt: { count: number; estimated_minutes: number; estimated_hours: number; severity: string; label: string };
}

export interface IssueCluster {
  cluster_id: string;
  title: string;
  total_count: number;
  severity: string;
  severity_breakdown: Record<string, number>;
  affected_services: string[];
  total_files: number;
  representative_file: string;
  root_cause: string;
  enterprise_recommendation: string;
  estimated_fix_time: number;
  cwe: string[];
  owasp: string[];
  standards_reference: string[];
}

export interface Hotspot {
  path: string;
  risk_score: number;
  reason: string;
  priority: string;
  estimated_effort: number;
  total_findings: number;
  severity_breakdown: Record<string, number>;
  top_issue: string;
}

export interface ServiceHealth {
  health_score: number;
  grade: string | null;
  security: number;
  performance: number;
  reliability: number;
  maintainability: number;
  total_findings: number;
  critical_count: number;
  high_count: number;
  recommendation: string;
}

export interface QuickWin {
  title: string;
  file: string;
  estimated_impact: string;
  estimated_time: number;
  priority: string;
  expected_score_improvement: number;
}

export interface Sprint {
  sprint_number: number;
  title: string;
  objectives: string[];
  tasks: string[];
  estimated_hours: number;
  expected_score_gain: number;
}

export interface OwnershipAssignment {
  recommended_team: string;
  total_findings: number;
  estimated_hours: number;
  categories: string[];
  rationale: string;
}

export interface EstimatedEffort {
  total_minutes: number;
  total_hours: number;
  total_days: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
}

export interface AIRecommendation {
  cluster_id: string;
  problem: string;
  root_cause: string;
  business_impact: string;
  enterprise_best_practice: string;
  recommended_refactor: string;
  expected_score_gain: number;
  estimated_hours: number;
  ai_confidence: string;
}

export interface RawFinding {
  rule_id: string;
  category: string;
  severity: string;
  title: string;
  file: string;
  description: string;
  recommendation: string;
  estimated_effort: number;
}

export interface EnterpriseGuide {
  id: string;
  job_id: string;

  // Legacy fields
  executive_summary: string | null;
  ai_executive_summary: string | null;
  critical_issues: unknown[] | null;
  high_issues: unknown[] | null;
  medium_issues: unknown[] | null;
  architecture_review: Record<string, unknown> | null;
  capacity_analysis: Record<string, unknown> | null;
  migration_path: unknown[] | null;

  // New structured fields
  repository_health: RepositoryHealth | null;
  engineering_scorecard: Record<string, ScorecardCategory> | null;
  business_risk: BusinessRisk | null;
  scalability_review: ScalabilityReview | null;
  technical_debt: TechnicalDebt | null;
  issue_clusters: IssueCluster[] | null;
  hotspots: Hotspot[] | null;
  service_health: Record<string, ServiceHealth> | null;
  quick_wins: QuickWin[] | null;
  sprint_roadmap: Record<string, Sprint> | null;
  deployment_readiness: Record<string, unknown> | null;
  release_recommendation: Record<string, unknown> | null;
  ownership: OwnershipAssignment[] | null;
  estimated_effort: EstimatedEffort | null;
  ai_recommendations: AIRecommendation[] | null;
  raw_findings: RawFinding[] | null;

  generated_at: string | null;
}

// ─── Job Statistics ────────────────────────────────────

export interface JobStatistics {
  findings_count: number;
  dead_code_count: number;
  error_findings_count: number;
  performance_metrics_count: number;
  simulation_results_count: number;
  enterprise_guide_exists: boolean;
  counts_by_severity: Record<string, number>;
  counts_by_category: Record<string, number>;
}

// ─── Analysis Insights (Sidebar) ────────────────────────

export interface AnalysisInsights {
  aiSummary: AiSummaryCard;
  priorityRecommendation: PriorityRecommendation;
  repositoryOverview: RepositoryOverview;
  engineStatus: EngineStatusItem[];
  metadata: AnalysisMetadata;
}

export interface AiSummaryCard {
  summary: string;
  isAiGenerated: boolean;
}

export interface PriorityRecommendation {
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  difficulty: 'high' | 'medium' | 'low';
  estimatedTime: string;
  findingId: string | null;
  category: string;
}

export interface LanguageBar {
  name: string;
  percentage: number;
  color: string;
}

export interface RepositoryOverview {
  languages: LanguageBar[];
  totalFiles: number;
  totalLines: number;
}

export interface EngineStatusItem {
  name: string;
  key: string;
  status: 'completed' | 'running' | 'failed' | 'skipped' | 'pending' | 'unavailable';
  duration: string | null;
  score: number | null;
  error: string | null;
}

export interface AnalysisMetadata {
  totalFiles: number;
  totalLines: number;
  classes: number;
  functions: number;
  endpoints: number;
  languages: string[];
  duration: string | null;
  startedAt: string | null;
  completedAt: string | null;
  branch: string;
  repoUrl: string;
  workspaceId: string;
}

// ─── Job Start Request ──────────────────────────────────

export interface StartAnalysisRequest {
  repo_id: string;
  workspace_id: string;
  repo_url: string;
  branch?: string;
  deep_scan?: boolean;
  depth?: number;
}

// Re-exported from types/api for the legacy analysis-api client
export type { Repository } from '@/types/api';
export type RepositoryProvider = 'github' | 'gitlab' | 'bitbucket';

export interface AnalysisResult {
  id: string;
  repository_id: string;
  status: string;
  score: number | null;
  summary: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}
