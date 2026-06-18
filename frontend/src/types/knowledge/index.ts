export type CanvasElementType =
  | 'text'
  | 'markdown'
  | 'code'
  | 'image'
  | 'pdf'
  | 'sticky_note'
  | 'diagram'
  | 'mindmap'
  | 'repository'
  | 'task'
  | 'ai'
  | 'rectangle'
  | 'circle'
  | 'triangle'
  | 'rhombus'
  | 'hexagon'
  | 'arrow'
  | 'start-node'
  | 'process-node'
  | 'decision-node'
  | 'end-node';

export type ShapeType = 'rectangle' | 'circle' | 'triangle' | 'rhombus' | 'hexagon';

export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface CanvasElement {
  id: string;
  type: CanvasElementType;
  position: Position;
  size: Size;
  rotation: number;
  zIndex: number;
  locked: boolean;
  visible: boolean;
  opacity: number;
  name?: string;
  data: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
}

export interface TextElementData {
  text: string;
  fontSize: number;
  fontWeight: 'normal' | 'bold' | 'semibold';
  fontFamily: string;
  color: string;
  backgroundColor: string | null;
  textAlign: 'left' | 'center' | 'right';
  padding: number;
}

export interface MarkdownElementData {
  source: string;
  backgroundColor: string | null;
}

export interface CodeElementData {
  code: string;
  language: string;
  theme: 'dark' | 'light';
  showLineNumbers: boolean;
  backgroundColor: string | null;
}

export interface ImageElementData {
  assetId: string;
  url: string;
  alt: string;
  originalWidth: number;
  originalHeight: number;
  objectFit: 'contain' | 'cover' | 'fill';
}

export interface PdfElementData {
  assetId: string;
  url: string;
  pageNumber: number;
  scale: number;
}

export interface StickyNoteElementData {
  text: string;
  color: string;
  fontSize: number;
}

export interface FlowchartNodeElementData {
  label: string;
  fillColor: string;
  strokeColor: string;
  strokeWidth: number;
}

export interface DiagramElementData {
  type: 'sequence' | 'class' | 'state' | 'entity';
  definition: string;
  backgroundColor: string | null;
}

export interface MindmapNodeData {
  id: string;
  label: string;
  children: MindmapNodeData[];
  color: string;
}

export interface MindmapElementData {
  root: MindmapNodeData;
  backgroundColor: string | null;
}

export interface RepositoryElementData {
  repositoryId: string;
  name: string;
  owner: string;
  url: string;
  description: string;
  showBranches: boolean;
  showReadme: boolean;
}

export interface TaskElementData {
  taskId: string;
  title: string;
  status: string;
  priority: string;
  assigneeId: string | null;
  projectId: string;
}

export interface AiElementData {
  prompt: string;
  response: string;
  model: string;
  status: 'generating' | 'complete' | 'error';
  generatedAt: string | null;
}

export interface ArrowElementData {
  startElementId: string | null;
  endElementId: string | null;
  points: [number, number][];
  controlPoint?: Position;
  arrowStyle: 'straight' | 'curved' | 'orthogonal';
  color: string;
  lineWidth: number;
}

export function resolveArrowPoints(d: Partial<ArrowElementData>): [number, number][] {
  if (d.points && d.points.length >= 2) return d.points;
  const sx = (d as Record<string, unknown>).startPoint
    ? ((d as Record<string, unknown>).startPoint as Position).x
    : 0;
  const sy = (d as Record<string, unknown>).startPoint
    ? ((d as Record<string, unknown>).startPoint as Position).y
    : 0;
  const ex = (d as Record<string, unknown>).endPoint
    ? ((d as Record<string, unknown>).endPoint as Position).x
    : 100;
  const ey = (d as Record<string, unknown>).endPoint
    ? ((d as Record<string, unknown>).endPoint as Position).y
    : 0;
  return [[sx, sy], [ex, ey]];
}

export interface ShapeElementData {
  fillColor: string;
  strokeColor: string;
  strokeWidth: number;
}

export interface AnchorPoint {
  x: number;
  y: number;
  side: 'top' | 'bottom' | 'left' | 'right';
}

export type ArrowStyle = 'straight' | 'curved' | 'orthogonal';

export interface CanvasViewport {
  x: number;
  y: number;
  zoom: number;
}

export interface CanvasState {
  elements: CanvasElement[];
  viewport: CanvasViewport;
  selectedElementIds: string[];
  clipboard: CanvasElement | null;
  gridEnabled: boolean;
  snapEnabled: boolean;
  gridSize: number;
}

export interface KnowledgeAssetReference {
  id: string;
  knowledgeSpaceId: string;
  fileName: string;
  fileSize: number;
  fileType: 'image' | 'pdf' | 'file' | 'code';
  mimeType: string;
  url: string | null;
  uploadedBy: string;
  createdAt: string;
  metadata: Record<string, unknown>;
}

export interface KnowledgeSpaceVersionSummary {
  id: string;
  versionNumber: number;
  createdBy: string;
  createdAt: string;
  description: string | null;
}

export interface KnowledgeWsEvent {
  type: 'canvas_update' | 'cursor_move' | 'element_lock' | 'user_join' | 'user_leave' | 'version_created';
  knowledgeSpaceId: string;
  userId: string;
  data: Record<string, unknown>;
  timestamp: string;
}
