'use client';

import { useMemo } from 'react';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';

const EMPTY_ARRAY: [] = [];

interface Props {
  spaceId: string;
}

export function PropertiesPanel({ spaceId }: Props) {
  const selectedElementIds = useKnowledgeStore(
    s => s.spaces[spaceId]?.selectedElementIds ?? EMPTY_ARRAY
  );
  const elements = useKnowledgeStore(
    s => s.spaces[spaceId]?.elements ?? EMPTY_ARRAY
  );
  const updateElement = useKnowledgeStore(s => s.updateElement);

  const selected = useMemo(
    () =>
      selectedElementIds.length === 1
        ? elements.find(e => e.id === selectedElementIds[0]) ?? null
        : null,
    [selectedElementIds, elements]
  );

  if (!selected) {
    return (
      <div className="p-4 text-center text-text-tertiary text-[13px]">
        {selectedElementIds.length > 1
          ? `${selectedElementIds.length} elements selected`
          : 'Select an element to edit its properties'}
      </div>
    );
  }

  const isShape = ['rectangle', 'circle', 'triangle', 'rhombus', 'hexagon'].includes(selected.type);
  const isText = selected.type === 'text' || selected.type === 'sticky_note';

  return (
    <div className="p-3 space-y-4 overflow-y-auto">
      <h3 className="text-[11px] font-semibold tracking-wider text-text-tertiary uppercase">
        Properties
      </h3>

      {/* Position */}
      <div className="space-y-2">
        <label className="text-[11px] text-text-tertiary">Position</label>
        <div className="grid grid-cols-2 gap-2">
          <input
            type="number"
            value={Math.round(selected.position.x)}
            onChange={e =>
              updateElement(spaceId, selected.id, {
                position: { ...selected.position, x: Number(e.target.value) },
              })
            }
            className="px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground w-full"
          />
          <input
            type="number"
            value={Math.round(selected.position.y)}
            onChange={e =>
              updateElement(spaceId, selected.id, {
                position: { ...selected.position, y: Number(e.target.value) },
              })
            }
            className="px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground w-full"
          />
        </div>
      </div>

      {/* Size */}
      <div className="space-y-2">
        <label className="text-[11px] text-text-tertiary">Size</label>
        <div className="grid grid-cols-2 gap-2">
          <input
            type="number"
            value={Math.round(selected.size.width)}
            onChange={e =>
              updateElement(spaceId, selected.id, {
                size: { ...selected.size, width: Number(e.target.value) },
              })
            }
            className="px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground w-full"
          />
          <input
            type="number"
            value={Math.round(selected.size.height)}
            onChange={e =>
              updateElement(spaceId, selected.id, {
                size: { ...selected.size, height: Number(e.target.value) },
              })
            }
            className="px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground w-full"
          />
        </div>
      </div>

      {/* Text properties */}
      {isText && (
        <div className="space-y-3 pt-1">
          <h4 className="text-[11px] font-semibold tracking-wider text-text-tertiary uppercase">
            Text
          </h4>

          {/* Font Size */}
          <div className="space-y-2">
            <label className="text-[11px] text-text-tertiary">Font Size</label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={8}
                max={96}
                value={(selected.data.fontSize as number) ?? 14}
                onChange={e =>
                  updateElement(spaceId, selected.id, {
                    data: { ...selected.data, fontSize: Number(e.target.value) },
                  })
                }
                className="flex-1 accent-venom-yellow"
              />
              <input
                type="number"
                min={8}
                max={96}
                value={(selected.data.fontSize as number) ?? 14}
                onChange={e =>
                  updateElement(spaceId, selected.id, {
                    data: { ...selected.data, fontSize: Math.max(8, Math.min(96, Number(e.target.value))) },
                  })
                }
                className="w-14 px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground text-center"
              />
            </div>
          </div>

          {/* Font Weight */}
          <div className="space-y-2">
            <label className="text-[11px] text-text-tertiary">Font Weight</label>
            <div className="flex gap-1">
              {(['normal', 'semibold', 'bold'] as const).map(w => (
                <button
                  key={w}
                  onClick={() =>
                    updateElement(spaceId, selected.id, {
                      data: { ...selected.data, fontWeight: w },
                    })
                  }
                  className={`flex-1 px-2 py-1 text-[11px] rounded border transition-colors ${
                    (selected.data.fontWeight ?? 'normal') === w
                      ? 'bg-venom-yellow/10 border-venom-yellow/40 text-venom-yellow'
                      : 'bg-krait-surface3 border-border text-text-secondary hover:text-foreground'
                  }`}
                >
                  {w.charAt(0).toUpperCase() + w.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Text Alignment */}
          <div className="space-y-2">
            <label className="text-[11px] text-text-tertiary">Alignment</label>
            <div className="flex gap-1">
              {(['left', 'center', 'right'] as const).map(a => (
                <button
                  key={a}
                  onClick={() =>
                    updateElement(spaceId, selected.id, {
                      data: { ...selected.data, textAlign: a },
                    })
                  }
                  className={`flex-1 px-2 py-1 text-[11px] rounded border transition-colors ${
                    (selected.data.textAlign ?? 'left') === a
                      ? 'bg-venom-yellow/10 border-venom-yellow/40 text-venom-yellow'
                      : 'bg-krait-surface3 border-border text-text-secondary hover:text-foreground'
                  }`}
                >
                  {a.charAt(0).toUpperCase() + a.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Text Color */}
          <div className="space-y-2">
            <label className="text-[11px] text-text-tertiary">Text Color</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={(selected.data.color as string) || '#e2e8f0'}
                onChange={e =>
                  updateElement(spaceId, selected.id, {
                    data: { ...selected.data, color: e.target.value },
                  })
                }
                className="w-8 h-8 p-0 border border-border rounded cursor-pointer bg-transparent"
              />
              <input
                type="text"
                value={(selected.data.color as string) || ''}
                onChange={e =>
                  updateElement(spaceId, selected.id, {
                    data: { ...selected.data, color: e.target.value || '#e2e8f0' },
                  })
                }
                className="flex-1 px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground font-mono"
              />
            </div>
          </div>

          {/* Padding */}
          <div className="space-y-2">
            <label className="text-[11px] text-text-tertiary">Padding</label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={0}
                max={48}
                value={(selected.data.padding as number) ?? 12}
                onChange={e =>
                  updateElement(spaceId, selected.id, {
                    data: { ...selected.data, padding: Number(e.target.value) },
                  })
                }
                className="flex-1 accent-venom-yellow"
              />
              <input
                type="number"
                min={0}
                max={48}
                value={(selected.data.padding as number) ?? 12}
                onChange={e =>
                  updateElement(spaceId, selected.id, {
                    data: { ...selected.data, padding: Math.max(0, Math.min(48, Number(e.target.value))) },
                  })
                }
                className="w-14 px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground text-center"
              />
            </div>
          </div>
        </div>
      )}

      {/* Rotation */}
      <div className="space-y-2">
        <label className="text-[11px] text-text-tertiary">Rotation</label>
        <input
          type="number"
          value={selected.rotation}
          onChange={e => updateElement(spaceId, selected.id, { rotation: Number(e.target.value) })}
          className="px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground w-full"
        />
      </div>

      {/* Opacity */}
      <div className="space-y-2">
        <label className="text-[11px] text-text-tertiary">Opacity</label>
        <input
          type="range"
          min={0}
          max={100}
          value={Math.round(selected.opacity * 100)}
          onChange={e =>
            updateElement(spaceId, selected.id, { opacity: Number(e.target.value) / 100 })
          }
          className="w-full accent-venom-yellow"
        />
        <span className="text-[11px] text-text-tertiary">
          {Math.round(selected.opacity * 100)}%
        </span>
      </div>

      {/* Shape style */}
      {isShape && (
        <div className="space-y-3 pt-1">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="shape-fill"
              checked={(selected.data.fillColor as string) !== 'transparent'}
              onChange={e =>
                updateElement(spaceId, selected.id, {
                  data: {
                    ...selected.data,
                    fillColor: e.target.checked ? '#cbd5e1' : 'transparent',
                  },
                })
              }
              className="accent-venom-yellow"
            />
            <label htmlFor="shape-fill" className="text-[13px] text-foreground cursor-pointer">
              Filled
            </label>
          </div>
          {(selected.data.fillColor as string) !== 'transparent' && (
            <div className="space-y-2">
              <label className="text-[11px] text-text-tertiary">Fill Color</label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={(selected.data.fillColor as string) || '#cbd5e1'}
                  onChange={e =>
                    updateElement(spaceId, selected.id, {
                      data: { ...selected.data, fillColor: e.target.value },
                    })
                  }
                  className="w-8 h-8 p-0 border border-border rounded cursor-pointer bg-transparent"
                />
                <input
                  type="text"
                  value={(selected.data.fillColor as string) || ''}
                  onChange={e =>
                    updateElement(spaceId, selected.id, {
                      data: { ...selected.data, fillColor: e.target.value || 'transparent' },
                    })
                  }
                  className="flex-1 px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground font-mono"
                />
              </div>
            </div>
          )}
          <div className="space-y-2">
            <label className="text-[11px] text-text-tertiary">Border Color</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={(selected.data.strokeColor as string) || '#cbd5e1'}
                onChange={e =>
                  updateElement(spaceId, selected.id, {
                    data: { ...selected.data, strokeColor: e.target.value },
                  })
                }
                className="w-8 h-8 p-0 border border-border rounded cursor-pointer bg-transparent"
              />
              <input
                type="text"
                value={(selected.data.strokeColor as string) || ''}
                onChange={e =>
                  updateElement(spaceId, selected.id, {
                    data: { ...selected.data, strokeColor: e.target.value || '#cbd5e1' },
                  })
                }
                className="flex-1 px-2 py-1 bg-krait-surface3 border border-border rounded text-[12px] text-foreground font-mono"
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-[11px] text-text-tertiary">Border Width</label>
            <input
              type="range"
              min={1}
              max={12}
              value={(selected.data.strokeWidth as number) ?? 2}
              onChange={e =>
                updateElement(spaceId, selected.id, {
                  data: { ...selected.data, strokeWidth: Number(e.target.value) },
                })
              }
              className="w-full accent-venom-yellow"
            />
            <span className="text-[11px] text-text-tertiary">
              {(selected.data.strokeWidth as number) ?? 2}px
            </span>
          </div>
        </div>
      )}

      {/* Lock */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={selected.locked}
          onChange={e => updateElement(spaceId, selected.id, { locked: e.target.checked })}
          className="accent-venom-yellow"
        />
        <span className="text-[13px] text-foreground">Locked</span>
      </label>

      {/* Element type info */}
      <div className="pt-3 border-t border-border">
        <div className="flex justify-between text-[12px]">
          <span className="text-text-tertiary">Type</span>
          <span className="text-foreground font-mono">{selected.type}</span>
        </div>
        <div className="flex justify-between text-[12px] mt-1">
          <span className="text-text-tertiary">Z-Index</span>
          <span className="text-foreground font-mono">{selected.zIndex}</span>
        </div>
      </div>
    </div>
  );
}
