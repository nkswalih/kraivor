export type ProjectStatus = 'planning' | 'active' | 'completed' | 'archived';
export type ProjectVisibility = 'private' | 'workspace';

export type TaskStatus =
  | 'backlog'
  | 'todo'
  | 'in_progress'
  | 'in_review'
  | 'blocked'
  | 'done'
  | 'cancelled';

export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';

export type TaskType =
  | 'feature'
  | 'bug'
  | 'improvement'
  | 'research'
  | 'spike'
  | 'documentation'
  | 'technical_debt'
  | 'incident';

export type TaskLinkType = 'blocks' | 'blocked_by' | 'duplicates' | 'relates_to' | 'caused_by';

export const TERMINAL_TASK_STATUSES: TaskStatus[] = ['done', 'cancelled'];
export const ACTIVE_TASK_STATUSES: TaskStatus[] = ['todo', 'in_progress', 'in_review', 'blocked'];

export const KANBAN_COLUMNS: TaskStatus[] = [
  'backlog',
  'todo',
  'in_progress',
  'in_review',
  'blocked',
  'done',
];

export interface ProjectRepository {
  id: string;
  github_repo: string;
}

export interface ProjectKnowledgeSpace {
  id: string;
  name: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  status: ProjectStatus;
  visibility: ProjectVisibility;
  owner_id: string;
  created_by: string;
  repository: ProjectRepository | null;
  knowledge_space: ProjectKnowledgeSpace | null;
  task_count: number;
  blocked_task_count: number;
  done_task_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreatePayload {
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  status?: ProjectStatus;
  visibility?: ProjectVisibility;
  repository_id?: string | null;
  knowledge_space_id?: string | null;
  owner_id?: string | null;
}

export type ProjectUpdatePayload = Partial<ProjectCreatePayload>;

export interface TaskRepositoryLink {
  id: string;
  repository_id: string;
  repository_github_repo: string;
}

export interface TaskKnowledgeLink {
  id: string;
  knowledge_space_id: string;
  space_name: string;
}

export interface TaskDependency {
  id: string;
  task_id: string;
  title: string;
  relationship_type: TaskLinkType;
}

export interface Task {
  id: string;
  project_id: string;
  parent_task_id: string | null;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  task_type: TaskType;
  assignee_id: string | null;
  reporter_id: string;
  due_date: string | null;
  estimate_points: number | null;
  position: number;
  subtask_count: number;
  repository_links: TaskRepositoryLink[];
  knowledge_links: TaskKnowledgeLink[];
  dependencies: TaskDependency[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TaskCreatePayload {
  project_id: string;
  title: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  task_type?: TaskType;
  assignee_id?: string | null;
  due_date?: string | null;
  estimate_points?: number | null;
  parent_task_id?: string | null;
}

export interface TaskUpdatePayload {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  task_type?: TaskType;
  assignee_id?: string | null;
  due_date?: string | null;
  estimate_points?: number | null;
}

export interface TaskStatusUpdatePayload {
  status: TaskStatus;
  position?: number | null;
}

export interface AddDependencyPayload {
  target_task_id: string;
  relationship_type: TaskLinkType;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AIRecommendations {
  suggested_tasks: unknown[];
  blocked_risk: unknown[];
  suggested_dependencies: unknown[];
  generated_at: string;
  phase: string;
}

export type KanbanBoard = Record<TaskStatus, Task[]>;
