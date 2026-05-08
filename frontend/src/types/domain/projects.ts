export interface Project {
  id: string;
  name: string;
  description?: string;
  workspaceId: string;
  status: ProjectStatus;
  priority: ProjectPriority;
  startDate?: string;
  dueDate?: string;
  completedAt?: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  members: string[];
  tasks: Task[];
}

export enum ProjectStatus {
  PLANNING = 'planning',
  ACTIVE = 'active',
  ON_HOLD = 'on_hold',
  COMPLETED = 'completed',
  ARCHIVED = 'archived',
}

export enum ProjectPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent',
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  projectId: string;
  status: TaskStatus;
  priority: ProjectPriority;
  assigneeId?: string;
  dueDate?: string;
  completedAt?: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  tags: string[];
  subtasks: Subtask[];
}

export enum TaskStatus {
  TODO = 'todo',
  IN_PROGRESS = 'in_progress',
  IN_REVIEW = 'in_review',
  DONE = 'done',
}

export interface Subtask {
  id: string;
  title: string;
  isCompleted: boolean;
}

export interface ProjectCreatePayload {
  name: string;
  description?: string;
  priority?: ProjectPriority;
  startDate?: string;
  dueDate?: string;
  memberIds?: string[];
}

export interface TaskCreatePayload {
  title: string;
  description?: string;
  projectId: string;
  priority?: ProjectPriority;
  assigneeId?: string;
  dueDate?: string;
  tags?: string[];
}