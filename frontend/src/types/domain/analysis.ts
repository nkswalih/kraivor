export interface Repository {
  id: string;
  name: string;
  fullName: string;
  provider: RepositoryProvider;
  url: string;
  defaultBranch: string;
  language: string;
  lastAnalyzed?: string;
  analysisStatus: AnalysisStatus;
}

export enum RepositoryProvider {
  GITHUB = 'github',
  GITLAB = 'gitlab',
  BITBUCKET = 'bitbucket',
}

export enum AnalysisStatus {
  PENDING = 'pending',
  ANALYZING = 'analyzing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface AnalysisResult {
  id: string;
  repositoryId: string;
  score: number;
  issues: AnalysisIssue[];
  recommendations: string[];
  metrics: AnalysisMetrics;
  createdAt: string;
}

export interface AnalysisIssue {
  severity: IssueSeverity;
  category: string;
  description: string;
  file?: string;
  line?: number;
  suggestion?: string;
}

export enum IssueSeverity {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  INFO = 'info',
}

export interface AnalysisMetrics {
  codeQuality: number;
  securityScore: number;
  testCoverage: number;
  documentationScore: number;
  maintainabilityScore: number;
}