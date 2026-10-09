'use client';

import { useState, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import type { Task, TaskStatus } from '@/types/domain/projects';
import { KANBAN_COLUMNS } from '@/types/domain/projects';
import { KanbanColumn } from '../tasks/kanban-column';
import { KanbanTaskCard } from '../tasks/kanban-task-card';
import { useUpdateTaskStatus } from '@/lib/hooks/use-projects';
import { Loader2 } from 'lucide-react';

interface ProjectBoardTabProps {
  workspaceId: string;
  projectId: string;
  tasks: Task[];
  isLoading: boolean;
}

export function ProjectBoardTab({
  workspaceId,
  projectId,
  tasks,
  isLoading,
}: ProjectBoardTabProps) {
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const updateStatus = useUpdateTaskStatus(workspaceId);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const columns = KANBAN_COLUMNS.reduce<Record<TaskStatus, Task[]>>(
    (acc, status) => {
      acc[status] = tasks.filter(t => t.status === status).sort((a, b) => a.position - b.position);
      return acc;
    },
    {} as Record<TaskStatus, Task[]>
  );

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const task = tasks.find(t => t.id === event.active.id);
      setActiveTask(task ?? null);
    },
    [tasks]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveTask(null);

      if (!over) return;

      const activeTaskId = active.id as string;
      const overContainerId = over.id as TaskStatus;

      const task = tasks.find(t => t.id === activeTaskId);
      if (!task) return;

      const targetStatus = KANBAN_COLUMNS.includes(overContainerId)
        ? overContainerId
        : (tasks.find(t => t.id === overContainerId)?.status ?? task.status);

      const targetColumnTasks = columns[targetStatus];

      let newPosition: number;
      if (KANBAN_COLUMNS.includes(overContainerId)) {
        const maxPos = targetColumnTasks.reduce((max, t) => Math.max(max, t.position), 0);
        newPosition = maxPos + 1000;
      } else {
        const overIndex = targetColumnTasks.findIndex(t => t.id === overContainerId);
        const above = targetColumnTasks[overIndex - 1];
        const below = targetColumnTasks[overIndex];

        if (!above) {
          newPosition = (below?.position ?? 1000) / 2;
        } else if (!below) {
          newPosition = (above?.position ?? 0) + 1000;
        } else {
          newPosition = (above.position + below.position) / 2;
        }
      }

      if (task.status !== targetStatus || Math.abs(task.position - newPosition) > 0.001) {
        updateStatus.mutate({
          taskId: activeTaskId,
          payload: { status: targetStatus, position: newPosition },
        });
      }
    },
    [tasks, columns, updateStatus]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-60">
        <Loader2 size={18} className="animate-spin text-[var(--venom-yellow)]" />
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 p-6 overflow-x-auto min-h-full">
        {KANBAN_COLUMNS.map(status => (
          <KanbanColumn
            key={status}
            status={status}
            tasks={columns[status]}
            projectId={projectId}
          />
        ))}
      </div>

      <DragOverlay>{activeTask && <KanbanTaskCard task={activeTask} isDragging />}</DragOverlay>
    </DndContext>
  );
}
